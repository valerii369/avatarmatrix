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
    PortraitMetaPattern, PortraitSummary, PortraitRawData,
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

    async def save_raw_results(self, portrait_id: str, system_name: str, raw_data: dict) -> None:
        """
        Flatten complex calculator output into granular dsb_raw_data rows.
        Splits data by groups (planets, aspects, houses, etc.) and saves a full snapshot.
        """
        # 0. Full Output Snapshot (For 100% Identicalness)
        self.session.add(PortraitRawData(
            portrait_id=portrait_id,
            system_name=system_name,
            data_group="full_output",
            data_key="engine_results",
            payload=raw_data,
        ))

        # 1. Planets
        for p in raw_data.get("planets", []):
            self.session.add(PortraitRawData(
                portrait_id=portrait_id,
                system_name=system_name,
                data_group="planets",
                data_key=p.get("name_en", "Unknown"),
                payload=p,
            ))

        # 2. Aspects
        for a in raw_data.get("aspects", []):
            p1, p2 = a.get("planet1"), a.get("planet2")
            asp_type = a.get("type")
            self.session.add(PortraitRawData(
                portrait_id=portrait_id,
                system_name=system_name,
                data_group="aspects",
                data_key=f"{p1}-{p2}-{asp_type}",
                payload=a,
            ))

        # 3. Houses (Full object + Detailed per house)
        houses = raw_data.get("houses", {})
        if houses:
            self.session.add(PortraitRawData(
                portrait_id=portrait_id,
                system_name=system_name,
                data_group="houses",
                data_key="all_houses",
                payload=houses,
            ))
            
            # Detailed house cusps/rulers
            cusps = houses.get("cusps", [])
            rulers = houses.get("rulers", {})
            for i, cusp_deg in enumerate(cusps):
                h_num = i + 1
                self.session.add(PortraitRawData(
                    portrait_id=portrait_id,
                    system_name=system_name,
                    data_group="houses_detailed",
                    data_key=f"House-{h_num}",
                    payload={
                        "house_num": h_num,
                        "cusp_degree": cusp_deg,
                        "ruler": rulers.get(str(h_num)),
                    },
                ))

        # 4. Technical Summary (Hemispheres, Elements, etc.)
        tech = raw_data.get("technical_summary", {})
        if tech:
            self.session.add(PortraitRawData(
                portrait_id=portrait_id,
                system_name=system_name,
                data_group="technical",
                data_key="summary",
                payload=tech,
            ))

        # 5. Core Points (Ascendant, MC, South Node)
        if "ascendant" in raw_data:
            self.session.add(PortraitRawData(
                portrait_id=portrait_id,
                system_name=system_name,
                data_group="points",
                data_key="ascendant",
                payload=raw_data["ascendant"],
            ))
        if "mc_degree" in raw_data:
            self.session.add(PortraitRawData(
                portrait_id=portrait_id,
                system_name=system_name,
                data_group="points",
                data_key="mc_degree",
                payload={"degree": raw_data["mc_degree"]},
            ))
        if "south_node" in raw_data:
            self.session.add(PortraitRawData(
                portrait_id=portrait_id,
                system_name=system_name,
                data_group="points",
                data_key="south_node",
                payload=raw_data["south_node"],
            ))
        if "geocoded" in raw_data:
            self.session.add(PortraitRawData(
                portrait_id=portrait_id,
                system_name=system_name,
                data_group="metadata",
                data_key="geocoding",
                payload=raw_data["geocoded"],
            ))

        # 6. Other groups (Stelliums, Arabic Parts, Patterns, Chains)
        for key in ["aspect_patterns", "arabic_parts", "stelliums", "dispositor_chains"]:
            group_data = raw_data.get(key)
            if group_data:
                self.session.add(PortraitRawData(
                    portrait_id=portrait_id,
                    system_name=system_name,
                    data_group=key,
                    data_key="collection",
                    payload=group_data if isinstance(group_data, dict) else {"items": group_data},
                ))

        await self.session.flush()
        logger.info(f"[Repo] Saved granular and full results for {system_name} in portrait {portrait_id}")

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

    async def generate_all_embeddings(self, portrait_id: str) -> None:
        """Генерирует и сохраняет эмбеддинги для всех записей портрета."""
        from sqlalchemy import select
        from app.dsb.storage.embeddings import generate_embedding_text, generate_embeddings_batch
        from app.dsb.storage.models import (
            PortraitFact, PortraitAspectChain, PortraitPattern,
            PortraitRecommendation, PortraitShadowAudit, PortraitMetaPattern
        )

        models_config = [
            (PortraitFact, "fact"),
            (PortraitAspectChain, "chain"),
            (PortraitPattern, "pattern"),
            (PortraitRecommendation, "recommendation"),
            (PortraitShadowAudit, "shadow"),
            (PortraitMetaPattern, "meta"),
        ]

        try:
            for model_cls, record_type in models_config:
                result = await self.session.execute(
                    select(model_cls).where(
                        model_cls.portrait_id == portrait_id,
                        model_cls.embedding.is_(None)
                    )
                )
                records = list(result.scalars().all())
                if not records:
                    continue

                texts = []
                for rec in records:
                    rec_dict = {k: v for k, v in rec.__dict__.items() if not k.startswith('_')}
                    texts.append(generate_embedding_text(rec_dict, record_type))

                for i in range(0, len(texts), 100):
                    batch_texts = texts[i:i+100]
                    batch_records = records[i:i+100]
                    embeddings = await generate_embeddings_batch(batch_texts)

                    for j, emb in enumerate(embeddings):
                        if emb is not None:
                            batch_records[j].embedding = emb

                await self.session.flush()
                logger.info(f"[Repo] Generated {len(records)} embeddings for {record_type}")
        except Exception as e:
            logger.error(f"[Repo] Failed to generate embeddings for portrait {portrait_id}: {e}")

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

    async def get_latest_ready_portrait_id(self, user_id: int) -> str | None:
        """Returns the latest portrait_id with status 'ready' for a user."""
        result = await self.session.execute(
            select(DigitalPortrait.id)
            .where(
                DigitalPortrait.user_id == user_id,
                DigitalPortrait.status == "ready"
            )
            .order_by(DigitalPortrait.created_at.desc())
        )
        row = result.scalars().first()
        return str(row) if row else None

    async def get_patterns_for_sphere(self, portrait_id: str, sphere: int) -> list[PortraitPattern]:
        result = await self.session.execute(
            select(PortraitPattern)
            .where(
                PortraitPattern.portrait_id == portrait_id,
                PortraitPattern.sphere == sphere,
            )
            .order_by(PortraitPattern.convergence_score.desc())
        )
        return list(result.scalars().all())

    async def get_recommendations_for_sphere(self, portrait_id: str, sphere: int) -> list[PortraitRecommendation]:
        result = await self.session.execute(
            select(PortraitRecommendation)
            .where(
                PortraitRecommendation.portrait_id == portrait_id,
                PortraitRecommendation.sphere == sphere,
            )
        )
        return list(result.scalars().all())

    async def get_shadows_for_sphere(self, portrait_id: str, sphere: int) -> list[PortraitShadowAudit]:
        result = await self.session.execute(
            select(PortraitShadowAudit)
            .where(
                PortraitShadowAudit.portrait_id == portrait_id,
                PortraitShadowAudit.sphere == sphere,
            )
            .order_by(PortraitShadowAudit.convergence_score.desc())
        )
        return list(result.scalars().all())
