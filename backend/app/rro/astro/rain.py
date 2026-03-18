import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.astrology.natal_chart import calculate_natal_chart, to_dict as chart_to_dict
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
# REMOVED: priority_engine, vector_matcher, llm_engine (Moved to L2/L3)
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

        # 1. Calculation (Strictly "Dry" Data)
        chart = calculate_natal_chart(birth_date, birth_time, lat, lon, tz_name)
        chart_dict = chart_to_dict(chart)
        aspects = calculate_aspects(chart_dict["planets"])
        aspects_dict = aspects_to_dict(aspects)

        # REMOVED: Level 1 Interpretations and Recommendations
        # These now happen in L2 (River) and L3 (Ocean)

        # 3. NatalChart Persistence
        natal_res = await db.execute(select(NatalChart).where(NatalChart.user_id == user_obj.id))
        natal = natal_res.scalar_one_or_none()
        if not natal:
            natal = NatalChart(user_id=user_obj.id)
            db.add(natal)
        
        natal.planets_json = chart_dict
        natal.aspects_json = aspects_dict
        # REMOVED: recommended_cards_json and sphere_descriptions_json
        natal.ascendant_sign = chart.ascendant_sign
        natal.ascendant_ruler = chart.ascendant_ruler
        natal.location_name = location_name
        
        # SAVE NEW TECH MARKERS
        natal.moon_phase = chart_dict.get("moon_phase")
        natal.technical_summary_json = chart_dict.get("technical_summary")
        natal.stelliums_json = chart_dict.get("stelliums")

        # 5. User Object Update
        user_obj.birth_date = birth_date
        user_obj.birth_time = birth_time
        user_obj.birth_place = location_name
        user_obj.birth_lat = lat
        user_obj.birth_lon = lon
        user_obj.birth_tz = tz_name
        user_obj.onboarding_done = True
        db.add(user_obj)

        # 4. Initialize CardProgress (Senior v3.2 Unified Matrix)
        # 264 cards total (12 spheres * 22 archetypes)
        spheres = [
            "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
            "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
            "EXPANSION", "STATUS", "VISION", "SPIRIT"
        ]
        for sphere in spheres:
            for arch_id in ARCHETYPE_IDS:
                cp = CardProgress(
                    user_id=user_obj.id,
                    sphere=sphere,
                    archetype_id=arch_id,
                    status=CardStatus.LOCKED
                )
                db.add(cp)

        await db.flush()
        return natal
