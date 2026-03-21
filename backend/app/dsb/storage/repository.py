from __future__ import annotations
"""
DSB Repository — CRUD операции для хранилища портретов.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.dsb.storage.models import (
    DigitalPortrait, PortraitFact, PortraitAspectChain,
    PortraitPattern, PortraitRecommendation, PortraitShadowAudit,
    PortraitMetaPattern, PortraitSummary,
)
from app.dsb.interpreters.schemas import UniversalInsightSchema

logger = logging.getLogger(__name__)


class PortraitRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Create ─────────────────────────────────────────────────────────────

    async def create_portrait(self, user_id: int, birth_data: dict, systems_used: list[str]) -> str:
        portrait = DigitalPortrait(
            user_id=user_id,
            birth_data=birth_data,
            systems_used=systems_used,
            status="generating",
        )
        self.session.add(portrait)
        await self.session.flush()
        return portrait.id

    async def save_facts(self, portrait_id: str, insights: list[UniversalInsightSchema]) -> None:
        for uis in insights:
            fact = PortraitFact(
                portrait_id=portrait_id,
                source_system=uis.source_system,
                sphere_primary=uis.primary_sphere,
                spheres_affected=uis.spheres_affected,
                position=uis.position,
                influence_level=uis.influence_level,
                light_aspect=uis.light_aspect,
                shadow_aspect=uis.shadow_aspect,
                energy_description=uis.energy_description,
                core_theme=uis.core_theme,
                developmental_task=uis.developmental_task,
                integration_key=uis.integration_key,
                triggers=uis.triggers,
                timing=uis.timing,
                book_references=uis.book_references,
                weight=uis.weight,
                confidence=uis.confidence,
                raw_uis=uis.model_dump(),
            )
            self.session.add(fact)
        await self.session.flush()
        logger.info(f"[Repo] Saved {len(insights)} facts for portrait {portrait_id}")

    async def save_sphere_synthesis(self, portrait_id: str, sphere_data: dict) -> None:
        sphere_num = sphere_data.get("sphere_num")

        # Layer 2: chains
        for chain in sphere_data.get("layer2_chains", []):
            self.session.add(PortraitAspectChain(
                portrait_id=portrait_id,
                sphere=sphere_num,
                chain_name=chain.get("chain_name", ""),
                systems_involved=chain.get("systems_involved", []),
                convergence_score=min(1.0, max(0.0, chain.get("convergence_score", 0))),
                description=chain.get("description", ""),
            ))

        # Layer 3: patterns
        for pattern in sphere_data.get("layer3_patterns", []):
            self.session.add(PortraitPattern(
                portrait_id=portrait_id,
                sphere=sphere_num,
                pattern_name=pattern.get("pattern_name", ""),
                formula=pattern.get("formula"),
                description=pattern.get("description", ""),
                systems_supporting=pattern.get("systems_supporting", []),
                convergence_score=pattern.get("convergence_score"),
            ))

        # Layer 4: recommendations
        for rec in sphere_data.get("layer4_recommendations", []):
            self.session.add(PortraitRecommendation(
                portrait_id=portrait_id,
                sphere=sphere_num,
                recommendation=rec.get("text", ""),
                source_systems=([rec["source_system"]] if "source_system" in rec else []),
                influence_level=rec.get("influence_level"),
                category=rec.get("category"),
            ))

        # Layer 5: shadow audit
        for risk in sphere_data.get("layer5_shadow_audit", []):
            self.session.add(PortraitShadowAudit(
                portrait_id=portrait_id,
                sphere=sphere_num,
                risk_name=risk.get("risk_name", ""),
                description=risk.get("description", ""),
                source_systems=risk.get("source_systems", []),
                convergence_score=risk.get("convergence_score"),
                antidote=risk.get("antidote", ""),
            ))

        await self.session.flush()

    async def save_meta_patterns(self, portrait_id: str, meta_data: dict) -> None:
        for pattern in meta_data.get("meta_patterns", []):
            self.session.add(PortraitMetaPattern(
                portrait_id=portrait_id,
                pattern_name=pattern.get("name", ""),
                spheres_involved=pattern.get("spheres_involved", []),
                description=pattern.get("description", ""),
                systems_supporting=pattern.get("systems_supporting", []),
                convergence_score=pattern.get("convergence_score"),
                key_manifestations=pattern.get("key_manifestations"),
            ))
        await self.session.flush()

    async def save_summaries(self, portrait_id: str, brief_data: dict) -> None:
        for i in range(1, 13):
            key = f"sphere_{i}_brief"
            if key in brief_data:
                self.session.add(PortraitSummary(
                    portrait_id=portrait_id,
                    sphere=i,
                    brief_text=brief_data[key],
                    is_overall=False,
                ))
        if "overall_brief" in brief_data:
            self.session.add(PortraitSummary(
                portrait_id=portrait_id,
                sphere=None,
                brief_text=brief_data["overall_brief"],
                is_overall=True,
            ))
        await self.session.flush()

    async def update_status(self, portrait_id: str, status: str) -> None:
        await self.session.execute(
            update(DigitalPortrait)
            .where(DigitalPortrait.id == portrait_id)
            .values(status=status)
        )
        await self.session.flush()

    # ─── Read ────────────────────────────────────────────────────────────────

    async def get_portrait(self, portrait_id: str) -> DigitalPortrait | None:
        result = await self.session.execute(
            select(DigitalPortrait).where(DigitalPortrait.id == portrait_id)
        )
        return result.scalar_one_or_none()

    async def get_portrait_by_user(self, user_id: int) -> DigitalPortrait | None:
        result = await self.session.execute(
            select(DigitalPortrait)
            .where(DigitalPortrait.user_id == user_id)
            .order_by(DigitalPortrait.created_at.desc())
        )
        return result.scalars().first()

    async def get_facts_for_sphere(self, portrait_id: str, sphere: int) -> list[PortraitFact]:
        result = await self.session.execute(
            select(PortraitFact)
            .where(
                PortraitFact.portrait_id == portrait_id,
                PortraitFact.sphere_primary == sphere,
            )
            .order_by(PortraitFact.weight.desc())
        )
        return list(result.scalars().all())

    async def get_brief_portrait(self, portrait_id: str) -> dict:
        result = await self.session.execute(
            select(PortraitSummary)
            .where(PortraitSummary.portrait_id == portrait_id)
        )
        summaries = result.scalars().all()
        output = {}
        for s in summaries:
            if s.is_overall:
                output["overall_brief"] = s.brief_text
            else:
                output[f"sphere_{s.sphere}_brief"] = s.brief_text
        return output
