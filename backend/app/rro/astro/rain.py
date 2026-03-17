import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.astrology.natal_chart import calculate_natal_chart, to_dict as chart_to_dict
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
from app.core.astrology.priority_engine import generate_recommended_cards
from app.core.astrology.vector_matcher import match_archetypes_to_spheres
from app.core.astrology.llm_engine import synthesize_sphere_descriptions
from app.agents.common import ARCHETYPE_IDS
from app.models.natal_chart import NatalChart
from app.models.card_progress import CardProgress, CardStatus

logger = logging.getLogger(__name__)

class AstroRain:
    """
    Astro Rain (Level 1): Handles raw architectural calculations and state persistence.
    """
    
    @staticmethod
    async def process_onboarding(db: AsyncSession, user_obj, birth_date, birth_time, lat, lon, tz_name, location_name) -> NatalChart:
        """
        Full Level 1 Pipeline:
        1. Calculate Planets/Aspects
        2. Generate L1 Interpretations (Sphere Descriptions)
        3. Determine Card Recommendations
        4. Persist to DB (NatalChart, CardProgress)
        """
        logger.info(f"AstroRain processing onboarding for user {user_obj.id}")

        # 1. Calculation
        chart = calculate_natal_chart(birth_date, birth_time, lat, lon, tz_name)
        chart_dict = chart_to_dict(chart)
        aspects = calculate_aspects(chart_dict["planets"])
        aspects_dict = aspects_to_dict(aspects)

        # 2. Rule + Vector Recommendations
        sphere_descriptions = await synthesize_sphere_descriptions(chart_dict, aspects_dict)
        recommended_rules = generate_recommended_cards(chart, aspects)
        recommended_vector = await match_archetypes_to_spheres(db, sphere_descriptions)

        # Merge recommendations
        combined_recommendations = []
        seen_rec = set()
        for r in recommended_rules:
            combined_recommendations.append(r)
            seen_rec.add((r.archetype_id, r.sphere))
        for r in recommended_vector:
            if (r.archetype_id, r.sphere) not in seen_rec:
                combined_recommendations.append(r)
                seen_rec.add((r.archetype_id, r.sphere))

        recommended_dict = [
            {"archetype_id": c.archetype_id, "sphere": c.sphere, "priority": c.priority, "reason": c.reason}
            for c in combined_recommendations
        ]

        # 3. CardProgress Persistence
        recommended_set = {(r.archetype_id, r.sphere): r for r in combined_recommendations}
        existing_result = await db.execute(select(CardProgress).where(CardProgress.user_id == user_obj.id))
        existing_cards = {(cp.archetype_id, cp.sphere): cp for cp in existing_result.scalars().all()}

        SPHERES_KEYS = ["IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS", "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION", "EXPANSION", "STATUS", "VISION", "SPIRIT"]

        for archetype_id in ARCHETYPE_IDS:
            for sphere in SPHERES_KEYS:
                key = (archetype_id, sphere)
                rec = recommended_set.get(key)
                if key in existing_cards:
                    cp = existing_cards[key]
                    if rec and not cp.is_recommended_astro:
                        cp.is_recommended_astro = True
                        cp.astro_priority = rec.priority
                        cp.astro_reason = rec.reason
                        if cp.status == CardStatus.LOCKED:
                            cp.status = CardStatus.RECOMMENDED
                        db.add(cp)
                else:
                    status = CardStatus.RECOMMENDED if rec else CardStatus.LOCKED
                    cp = CardProgress(
                        user_id=user_obj.id, archetype_id=archetype_id, sphere=sphere, status=status,
                        is_recommended_astro=rec is not None,
                        astro_priority=rec.priority if rec else None,
                        astro_reason=rec.reason if rec else None
                    )
                    db.add(cp)

        # 4. NatalChart Persistence
        natal_res = await db.execute(select(NatalChart).where(NatalChart.user_id == user_obj.id))
        natal = natal_res.scalar_one_or_none()
        if not natal:
            natal = NatalChart(user_id=user_obj.id)
            db.add(natal)
        
        natal.planets_json = chart_dict
        natal.aspects_json = aspects_dict
        natal.recommended_cards_json = recommended_dict
        natal.sphere_descriptions_json = sphere_descriptions
        natal.ascendant_sign = chart.ascendant_sign
        natal.ascendant_ruler = chart.ascendant_ruler
        natal.location_name = location_name

        # 5. User Object Update
        user_obj.birth_date = birth_date
        user_obj.birth_time = birth_time
        user_obj.birth_place = location_name
        user_obj.birth_lat = lat
        user_obj.birth_lon = lon
        user_obj.birth_tz = tz_name
        user_obj.onboarding_done = True
        db.add(user_obj)

        await db.flush()
        return natal
