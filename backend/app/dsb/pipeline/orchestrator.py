from __future__ import annotations
"""
PortraitOrchestrator — главный пайплайн Digital Soul Blueprint.

Автоматически масштабируется от 1 до 8 учений.
На старте: 1 калькулятор + 1 агент (western_astrology).
Все 8 калькуляторов запускаются (сохраняют данные), но только активные
проходят через интерпретацию и синтез.
"""

import asyncio
import importlib
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.dsb.calculators.base import BirthData, Calculator
from app.dsb.interpreters.base import InterpretationAgent
from app.dsb.interpreters.schemas import UniversalInsightSchema
from app.dsb.synthesis.merger import Merger
from app.dsb.synthesis.sphere_agent import SphereAgent
from app.dsb.synthesis.meta_agent import MetaAgent
from app.dsb.synthesis.compressor import Compressor
from app.dsb.storage.repository import PortraitRepository
from app.dsb.config import SYSTEM_REGISTRY, ACTIVE_SYSTEMS

logger = logging.getLogger(__name__)


def _import_class(dotted_path: str):
    """Динамический импорт класса по пути 'module.path.ClassName'."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class PortraitOrchestrator:
    """
    Оркестрирует полный цикл генерации портрета.

    Принцип:
    - Все калькуляторы из SYSTEM_REGISTRY (runs_calculator=True) запускаются параллельно
    - Только активные (active=True) проходят интерпретацию и синтез
    - Ядро Слоя 3 (Merger → SphereAgents → Meta → Compressor) не меняется
    """

    def __init__(self):
        self._all_calculators: list[tuple[str, Calculator]] = []
        self._active_agents: list[tuple[str, InterpretationAgent]] = []
        self._active_system_names: list[str] = []
        self._load_systems()

    def _load_systems(self):
        """Инициализирует калькуляторы и агентов по реестру."""
        for name, cfg in SYSTEM_REGISTRY.items():
            if cfg.get("runs_calculator", False):
                try:
                    calc_cls = _import_class(cfg["calculator"])
                    self._all_calculators.append((name, calc_cls()))
                    logger.info(f"[Orchestrator] Loaded calculator: {name}")
                except Exception as e:
                    logger.error(f"[Orchestrator] Failed to load calculator {name}: {e}")

            if cfg.get("active", False):
                try:
                    agent_cls = _import_class(cfg["agent"])
                    self._active_agents.append((name, agent_cls()))
                    self._active_system_names.append(name)
                    logger.info(f"[Orchestrator] Loaded active agent: {name}")
                except Exception as e:
                    logger.error(f"[Orchestrator] Failed to load agent {name}: {e}")

    async def generate(
        self,
        birth_data: BirthData,
        user_id: int,
        session: AsyncSession,
    ) -> str:
        """
        Запускает полный пайплайн генерации портрета.

        Returns: portrait_id (UUID string)
        """
        repo = PortraitRepository(session)

        # ─── Создать запись портрета ─────────────────────────────────────
        portrait_id = await repo.create_portrait(
            user_id=user_id,
            birth_data=birth_data.model_dump(mode="json"),
            systems_used=self._active_system_names,
        )
        await session.commit()
        logger.info(f"[Orchestrator] Portrait {portrait_id} created for user {user_id}")

        try:
            # ═══ СЛОЙ 1: Расчёты (все калькуляторы параллельно) ════════
            logger.info(f"[Orchestrator] Layer 1: running {len(self._all_calculators)} calculators...")
            raw_results = await asyncio.gather(*[
                calc.calculate(birth_data)
                for _, calc in self._all_calculators
            ], return_exceptions=True)

            # Сохранить сырые результаты для всех систем
            for (name, _), result in zip(self._all_calculators, raw_results):
                if not isinstance(result, Exception):
                    await repo.save_raw_results(portrait_id, name, result.get("raw_data", {}))
            await session.commit()

            # Оставляем только успешные результаты для активных агентов
            active_raw = []
            for (name, _), result in zip(self._all_calculators, raw_results):
                if isinstance(result, Exception):
                    logger.error(f"[Orchestrator] Calculator {name} failed: {result}")
                    if name in self._active_system_names:
                        active_raw.append(None)
                elif name in self._active_system_names:
                    active_raw.append(result)

            # ═══ СЛОЙ 2: Интерпретация (только активные агенты) ════════
            logger.info(f"[Orchestrator] Layer 2: running {len(self._active_agents)} agents...")
            interpretation_tasks = []
            for i, (name, agent) in enumerate(self._active_agents):
                raw = active_raw[i] if i < len(active_raw) and active_raw[i] is not None else {}
                interpretation_tasks.append(agent.interpret(raw.get("raw_data", {})))

            interpretations = await asyncio.gather(*interpretation_tasks, return_exceptions=True)

            all_insights: list[UniversalInsightSchema] = []
            for (name, _), result in zip(self._active_agents, interpretations):
                if isinstance(result, Exception):
                    logger.error(f"[Orchestrator] Agent {name} failed: {result}")
                else:
                    all_insights.extend(result)

            logger.info(f"[Orchestrator] Total UIS objects: {len(all_insights)}")

            # Сохранить факты
            await repo.save_facts(portrait_id, all_insights)
            await session.commit()

            # ═══ СЛОЙ 3a: Merger ════════════════════════════════════════
            logger.info("[Orchestrator] Layer 3a: Merging by spheres...")
            merger = Merger()
            spheres_data = merger.merge([all_insights])
            # Примечание: merger.merge ожидает list[list[UIS]] — передаём один поток

            # ═══ СЛОЙ 3b: 12 Sphere Agents (параллельно) ════════════════
            logger.info("[Orchestrator] Layer 3b: Synthesizing 12 spheres (parallel)...")
            sphere_agent = SphereAgent()
            sphere_tasks = [
                sphere_agent.synthesize(
                    sphere_num=i,
                    insights=spheres_data.get(f"sphere_{i}", []),
                    active_systems=self._active_system_names,
                )
                for i in range(1, 13)
            ]
            sphere_portraits = await asyncio.gather(*sphere_tasks)

            # Сохранить синтез каждой сферы
            for sp in sphere_portraits:
                await repo.save_sphere_synthesis(portrait_id, sp)
            await session.commit()

            # ═══ СЛОЙ 3c: Meta Agent ════════════════════════════════════
            logger.info("[Orchestrator] Layer 3c: Meta Agent (super-patterns)...")
            meta_agent = MetaAgent()
            meta_patterns = await meta_agent.find_patterns(list(sphere_portraits))
            await repo.save_meta_patterns(portrait_id, meta_patterns)
            await session.commit()

            # ═══ СЛОЙ 3d: Compressor ════════════════════════════════════
            logger.info("[Orchestrator] Layer 3d: Compressor (brief format)...")
            compressor = Compressor()
            brief = await compressor.compress(list(sphere_portraits), meta_patterns)
            await repo.save_summaries(portrait_id, brief)

            # ═══ Готово ═════════════════════════════════════════════════
            # Генерируем синтетический UserPrint для старого MasterHubView
            from app.dsb.synthesis.master_hub_adapter import generate_user_print_from_dsb
            await generate_user_print_from_dsb(user_id, session, brief, meta_patterns)

            await repo.update_status(portrait_id, "ready")
            await session.commit()
            logger.info(f"[Orchestrator] Portrait {portrait_id} READY")

            # Notification to user
            from app.models.user import User
            from sqlalchemy import select
            user_res = await session.execute(select(User).where(User.id == user_id))
            user_obj = user_res.scalar_one_or_none()
            if user_obj and user_obj.tg_id:
                msg = (
                    "✅ <b>Твой DSB Паспорт готов!</b>\n\n"
                    "Расчёт по 12 сферам и теневой компас полностью синтезированы.\n✨ "
                    "Переходи во вкладку «О тебе», чтобы открыть подробности."
                )
                from app.services.notification import NotificationService
                await NotificationService.send_tg_message(user_obj.tg_id, msg)

        except Exception as e:
            logger.exception(f"[Orchestrator] Pipeline failed for portrait {portrait_id}: {e}")
            await repo.update_status(portrait_id, "error")
            await session.commit()

        return portrait_id
