import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.astrology.natal_chart import calculate_natal_chart, to_dict as chart_to_dict
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
from app.core.astrology.priority_engine import generate_recommended_cards
from app.core.astrology.vector_matcher import match_archetypes_to_spheres
from app.models.natal_chart import NatalChart
from app.models.card_progress import CardProgress, CardStatus

logger = logging.getLogger(__name__)

class AstroRain:
    """
    Astro Rain (Level 1): Handles raw architectural calculations and state persistence.
    LLM synthesis (sphere_descriptions) is done in background pipeline (L2/River).
    """
    
    @staticmethod
    async def process_onboarding(db: AsyncSession, user_obj, birth_date, birth_time, lat, lon, tz_name, location_name) -> NatalChart:
        """
        Fast Level 1 Pipeline:
        1. Calculate Planets/Aspects (deterministic, no LLM)
        2. Determine Card Recommendations (vector + rule-based)
        3. Persist to DB (NatalChart, CardProgress)
        LLM synthesis goes to background (Level 2 River).
        """
        logger.info(f"AstroRain processing onboarding for user {user_obj.id}")

        # 1. Calculation (fast, deterministic)
        chart = calculate_natal_chart(birth_date, birth_time, lat, lon, tz_name)
        chart_dict = chart_to_dict(chart)
        aspects = calculate_aspects(chart_dict["planets"])
        aspects_dict = aspects_to_dict(aspects)

        # 2. Rule-based Card Recommendations (no LLM needed here)
        recommended_rules = generate_recommended_cards(chart, aspects)

        recommended_dict = [
            {"archetype_id": c.archetype_id, "sphere": c.sphere, "priority": c.priority, "reason": c.reason}
            for c in recommended_rules
        ]

        # 3. NatalChart Persistence
        natal_res = await db.execute(select(NatalChart).where(NatalChart.user_id == user_obj.id))
        natal = natal_res.scalar_one_or_none()
        if not natal:
            natal = NatalChart(user_id=user_obj.id)
            db.add(natal)
        
        natal.planets_json = chart_dict
        natal.aspects_json = aspects_dict
        natal.recommended_cards_json = recommended_dict
        natal.sphere_descriptions_json = {}  # Will be filled by River (L2 background)
        natal.ascendant_sign = chart.ascendant_sign
        natal.ascendant_ruler = chart.ascendant_ruler
        natal.location_name = location_name

        # 4. User Object Update
        user_obj.birth_date = birth_date
        user_obj.birth_time = birth_time
        user_obj.birth_place = location_name
        user_obj.birth_lat = lat
        user_obj.birth_lon = lon
        user_obj.birth_tz = tz_name
        user_obj.onboarding_done = True
        db.add(user_obj)

        # 5. CardProgress: create locked rows for all 264 cards
        await _ensure_card_progress(db, user_obj.id, recommended_dict)

        await db.flush()
        return natal


async def _ensure_card_progress(db: AsyncSession, user_id: int, recommended_dict: list):
    """Create or update CardProgress rows for the user."""
    from app.agents.common import ARCHETYPE_IDS
    SPHERES = [
        "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
        "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
        "EXPANSION", "STATUS", "VISION", "SPIRIT"
    ]
    
    recommended_set = {(r["archetype_id"], r["sphere"]) for r in recommended_dict}
    
    # Get existing progress rows
    existing_res = await db.execute(
        select(CardProgress).where(CardProgress.user_id == user_id)
    )
    existing = {(cp.archetype_id, cp.sphere): cp for cp in existing_res.scalars().all()}

    for sphere in SPHERES:
        for arch_id in ARCHETYPE_IDS:
            key = (arch_id, sphere)
            is_recommended = key in recommended_set
            
            if key not in existing:
                # Create new locked card
                cp = CardProgress(
                    user_id=user_id,
                    archetype_id=arch_id,
                    sphere=sphere,
                    status=CardStatus.RECOMMENDED if is_recommended else CardStatus.LOCKED,
                    is_recommended_astro=is_recommended,
                )
                db.add(cp)
            elif is_recommended and existing[key].status == CardStatus.LOCKED:
                # Upgrade locked → recommended
                existing[key].status = CardStatus.RECOMMENDED
                existing[key].is_recommended_astro = True
