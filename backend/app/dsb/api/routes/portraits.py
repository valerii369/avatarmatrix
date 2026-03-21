from __future__ import annotations
"""
DSB API Routes — FastAPI endpoints для Digital Soul Blueprint.

Все эндпоинты из секции 15, задача 1.5.
Монтируется на /api/dsb/
"""

import asyncio
import logging
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dsb.calculators.base import BirthData
from app.dsb.config import SYSTEM_REGISTRY, ACTIVE_SYSTEMS, SPHERE_NAMES
from app.dsb.pipeline.orchestrator import PortraitOrchestrator
from app.dsb.storage.repository import PortraitRepository
from app.dsb.storage.search import semantic_search
from app.core.astrology.natal_chart import geocode_place

logger = logging.getLogger(__name__)
router = APIRouter()

# Единственный экземпляр оркестратора
_orchestrator: PortraitOrchestrator | None = None


def get_orchestrator() -> PortraitOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PortraitOrchestrator()
    return _orchestrator


# ─── Schemas ─────────────────────────────────────────────────────────────────

class GeneratePortraitRequest(BaseModel):
    date: datetime.date = Field(..., description="Дата рождения YYYY-MM-DD")
    time: Optional[datetime.time] = Field(None, description="Время рождения HH:MM")
    place: str = Field(..., description="Место рождения (город, страна)")
    full_name: Optional[str] = Field(None, description="ФИО (для нумерологии)")
    user_id: int = Field(..., description="ID пользователя")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Вопрос для поиска по портрету")
    top_k: int = Field(default=10, le=50)
    spheres_filter: Optional[list[int]] = None
    influence_filter: Optional[list[str]] = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/portraits/generate", summary="Запустить генерацию портрета")
async def generate_portrait(
    request: GeneratePortraitRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    orchestrator: PortraitOrchestrator = Depends(get_orchestrator),
):
    """
    Запускает полный DSB пайплайн генерации портрета.
    Возвращает portrait_id немедленно, генерация идёт в фоне.
    """
    # Геокодирование
    try:
        lat, lon, tz = await geocode_place(request.place)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Не удалось геокодировать место: {e}")

    birth_data = BirthData(
        date=request.date,
        time=request.time,
        place=request.place,
        lat=lat,
        lon=lon,
        timezone=tz,
        full_name=request.full_name,
    )

    # Создаём запись и запускаем в фоне
    repo = PortraitRepository(session)
    portrait_id = await repo.create_portrait(
        user_id=request.user_id,
        birth_data=birth_data.model_dump(mode="json"),
        systems_used=ACTIVE_SYSTEMS,
    )
    await session.commit()

    async def run_pipeline():
        from app.database import async_session_factory
        async with async_session_factory() as bg_session:
            try:
                # Используем оркестратор без повторного create_portrait
                merger_orchestrator = PortraitOrchestrator()
                from app.dsb.storage.repository import PortraitRepository as Repo
                bg_repo = Repo(bg_session)

                # Layer 1 — calculators
                raw_results = await asyncio.gather(*[
                    calc.calculate(birth_data)
                    for _, calc in merger_orchestrator._all_calculators
                ], return_exceptions=True)

                # Layer 2 — active agents
                from app.dsb.interpreters.schemas import UniversalInsightSchema
                active_raw = []
                for (name, _), result in zip(merger_orchestrator._all_calculators, raw_results):
                    if name in merger_orchestrator._active_system_names:
                        active_raw.append(
                            result if not isinstance(result, Exception) else None
                        )

                interpretations = await asyncio.gather(*[
                    agent.interpret((active_raw[i] or {}).get("raw_data", {}))
                    for i, (_, agent) in enumerate(merger_orchestrator._active_agents)
                ], return_exceptions=True)

                all_insights: list[UniversalInsightSchema] = []
                for result in interpretations:
                    if not isinstance(result, Exception):
                        all_insights.extend(result)

                await bg_repo.save_facts(portrait_id, all_insights)
                await bg_session.commit()

                # Layer 3 — Synthesis
                from app.dsb.synthesis.merger import Merger
                from app.dsb.synthesis.sphere_agent import SphereAgent
                from app.dsb.synthesis.meta_agent import MetaAgent
                from app.dsb.synthesis.compressor import Compressor

                spheres_data = Merger().merge([all_insights])
                sphere_agent = SphereAgent()
                sphere_portraits = await asyncio.gather(*[
                    sphere_agent.synthesize(i, spheres_data.get(f"sphere_{i}", []),
                                            merger_orchestrator._active_system_names)
                    for i in range(1, 13)
                ])

                for sp in sphere_portraits:
                    await bg_repo.save_sphere_synthesis(portrait_id, sp)
                await bg_session.commit()

                meta = await MetaAgent().find_patterns(list(sphere_portraits))
                await bg_repo.save_meta_patterns(portrait_id, meta)

                brief = await Compressor().compress(list(sphere_portraits), meta)
                await bg_repo.save_summaries(portrait_id, brief)

                await bg_repo.update_status(portrait_id, "ready")
                await bg_session.commit()
                logger.info(f"[API] Portrait {portrait_id} ready")

            except Exception as e:
                logger.exception(f"[API] Background pipeline failed: {e}")
                from app.database import async_session_factory as sf
                async with sf() as err_session:
                    err_repo = Repo(err_session)
                    await err_repo.update_status(portrait_id, "error")
                    await err_session.commit()

    background_tasks.add_task(run_pipeline)

    return {
        "portrait_id": portrait_id,
        "status": "generating",
        "systems": ACTIVE_SYSTEMS,
        "message": "Генерация запущена. Проверяйте статус через GET /api/dsb/portraits/{id}/status",
    }


@router.get("/portraits/{portrait_id}/status", summary="Статус генерации портрета")
async def get_portrait_status(
    portrait_id: str,
    session: AsyncSession = Depends(get_db),
):
    repo = PortraitRepository(session)
    portrait = await repo.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=404, detail="Portrait not found")

    return {
        "portrait_id": portrait_id,
        "status": portrait.status,
        "systems_used": portrait.systems_used,
        "version": portrait.version,
        "created_at": portrait.created_at.isoformat(),
    }


@router.get("/portraits/{portrait_id}", summary="Полный портрет")
async def get_portrait(
    portrait_id: str,
    session: AsyncSession = Depends(get_db),
):
    repo = PortraitRepository(session)
    portrait = await repo.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=404, detail="Portrait not found")
    if portrait.status != "ready":
        raise HTTPException(
            status_code=202,
            detail=f"Portrait is {portrait.status}. Try again later.",
        )

    # Собираем все факты по сферам
    from sqlalchemy import select
    from app.dsb.storage.models import (
        PortraitFact, PortraitAspectChain, PortraitPattern,
        PortraitRecommendation, PortraitShadowAudit, PortraitMetaPattern,
        PortraitSummary
    )

    async def load(model, portrait_id=portrait_id):
        result = await session.execute(
            select(model).where(model.portrait_id == portrait_id)
        )
        return result.scalars().all()

    facts = await load(PortraitFact)
    chains = await load(PortraitAspectChain)
    patterns = await load(PortraitPattern)
    recs = await load(PortraitRecommendation)
    shadows = await load(PortraitShadowAudit)
    metas = await load(PortraitMetaPattern)
    summaries = await load(PortraitSummary)

    # Structure by sphere
    spheres = {}
    for i in range(1, 13):
        spheres[str(i)] = {
            "name": SPHERE_NAMES[i],
            "layer1_facts": [
                {"position": f.position, "source": f.source_system,
                 "influence": f.influence_level, "light": f.light_aspect,
                 "shadow": f.shadow_aspect, "core_theme": f.core_theme}
                for f in facts if f.sphere_primary == i
            ],
            "layer2_chains": [
                {"name": c.chain_name, "convergence": c.convergence_score,
                 "description": c.description}
                for c in chains if c.sphere == i
            ],
            "layer3_patterns": [
                {"name": p.pattern_name, "formula": p.formula,
                 "description": p.description, "convergence": p.convergence_score}
                for p in patterns if p.sphere == i
            ],
            "layer4_recommendations": [
                {"text": r.recommendation, "influence": r.influence_level,
                 "category": r.category}
                for r in recs if r.sphere == i
            ],
            "layer5_shadow_audit": [
                {"risk": s.risk_name, "description": s.description,
                 "antidote": s.antidote, "convergence": s.convergence_score}
                for s in shadows if s.sphere == i
            ],
        }

    return {
        "portrait_id": portrait_id,
        "status": portrait.status,
        "systems_used": portrait.systems_used,
        "birth_data": portrait.birth_data,
        "spheres": spheres,
        "meta_patterns": [
            {"name": m.pattern_name, "spheres": m.spheres_involved,
             "description": m.description, "convergence": m.convergence_score}
            for m in metas
        ],
    }


@router.get("/portraits/{portrait_id}/sphere/{sphere_num}", summary="Одна сфера")
async def get_sphere(
    portrait_id: str,
    sphere_num: int,
    format: str = "full",
    session: AsyncSession = Depends(get_db),
):
    if sphere_num < 1 or sphere_num > 12:
        raise HTTPException(status_code=422, detail="Sphere must be 1-12")

    repo = PortraitRepository(session)
    portrait = await repo.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=404, detail="Portrait not found")

    if format == "brief":
        brief = await repo.get_brief_portrait(portrait_id)
        return {
            "sphere": sphere_num,
            "name": SPHERE_NAMES[sphere_num],
            "brief": brief.get(f"sphere_{sphere_num}_brief", ""),
        }

    facts = await repo.get_facts_for_sphere(portrait_id, sphere_num)
    return {
        "sphere": sphere_num,
        "name": SPHERE_NAMES[sphere_num],
        "facts": [
            {"position": f.position, "influence": f.influence_level,
             "light": f.light_aspect, "shadow": f.shadow_aspect,
             "core_theme": f.core_theme, "triggers": f.triggers}
            for f in facts
        ],
    }


@router.get("/portraits/{portrait_id}/brief", summary="Краткий формат портрета")
async def get_brief_portrait(
    portrait_id: str,
    session: AsyncSession = Depends(get_db),
):
    repo = PortraitRepository(session)
    portrait = await repo.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=404, detail="Portrait not found")

    brief = await repo.get_brief_portrait(portrait_id)
    return {
        "portrait_id": portrait_id,
        "systems_used": portrait.systems_used,
        "brief": brief,
    }


@router.post("/portraits/{portrait_id}/search", summary="Семантический поиск по портрету")
async def search_portrait(
    portrait_id: str,
    request: SearchRequest,
    session: AsyncSession = Depends(get_db),
):
    repo = PortraitRepository(session)
    portrait = await repo.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=404, detail="Portrait not found")

    results = await semantic_search(
        session=session,
        portrait_id=portrait_id,
        query=request.query,
        top_k=request.top_k,
        spheres_filter=request.spheres_filter,
        influence_filter=request.influence_filter,
    )

    return {
        "portrait_id": portrait_id,
        "query": request.query,
        "results": results,
    }


@router.get("/systems", summary="Список учений (активные и планируемые)")
async def get_systems():
    active = [name for name, cfg in SYSTEM_REGISTRY.items() if cfg.get("active")]
    planned = [name for name, cfg in SYSTEM_REGISTRY.items() if not cfg.get("active")]
    return {
        "active": active,
        "planned": planned,
        "note": "Архитектура поддерживает все 8 учений. Старт с 1.",
    }


@router.post("/portraits/{portrait_id}/regenerate", summary="Перегенерация портрета")
async def regenerate_portrait(
    portrait_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    """Перезапускает пайплайн — используется при подключении нового учения."""
    repo = PortraitRepository(session)
    portrait = await repo.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=404, detail="Portrait not found")

    await repo.update_status(portrait_id, "generating")
    await session.commit()

    # TODO: реализовать полный rerrun с сохранёнными birth_data
    return {
        "portrait_id": portrait_id,
        "status": "generating",
        "message": "Перегенерация запущена (TODO: реализовать полный rerrun)",
    }
