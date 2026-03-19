import datetime
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.astrology.natal_chart import calculate_natal_chart, to_dict as chart_to_dict
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
# REMOVED: priority_engine, vector_matcher, llm_engine (Moved to L2/L3)
from app.agents.common import ARCHETYPE_IDS
from app.models.natal_chart import NatalChart
from app.models.card_progress import CardProgress, CardStatus
from app.rro.astro.api_client import AstrologyAPIClient
import pytz

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
        
        # 2. Enrichment: Fetch professional data from astrologyapi.com (Synchronous now)
        try:
            h, m = map(int, birth_time.split(":"))
            tz = pytz.timezone(tz_name)
            dt_combined = datetime.datetime.combine(birth_date, datetime.time(h, m))
            offset = tz.utcoffset(dt_combined).total_seconds() / 3600.0

            client = AstrologyAPIClient()
            api_data = await client.get_western_horoscope(
                day=birth_date.day,
                month=birth_date.month,
                year=birth_date.year,
                hour=h,
                minute=m,
                lat=lat,
                lon=lon,
                tzone=offset
            )
            natal.api_raw_json = api_data
            logger.info(f"AstrologyAPI enrichment successful for user {user_obj.id}")
        except Exception as api_err:
            logger.error(f"AstrologyAPI enrichment failed during onboarding: {api_err}")

        # 3. SAVE TECH MARKERS (Senior +++)
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
        # Clear old rows if retaking onboarding
        await db.execute(delete(CardProgress).where(CardProgress.user_id == user_obj.id))
        
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

    @staticmethod
    async def enrich_with_api(db: AsyncSession, natal_id: int):
        """
        Level 1 Enrichment: Fetch professional data from astrologyapi.com
        and store it in natal_charts.api_raw_json.
        """
        from app.models.user import User
        res = await db.execute(
            select(NatalChart, User)
            .join(User, User.id == NatalChart.user_id)
            .where(NatalChart.id == natal_id)
        )
        row = res.fetchone()
        if not row:
            logger.error(f"NatalChart {natal_id} not found for enrichment")
            return

        natal, user = row
        client = AstrologyAPIClient()
        
        try:
            # Prepare birth data for API
            # Note: hour:min parsing from user.birth_time (HH:mm)
            h, m = map(int, user.birth_time.split(":"))
            
            # Calculate tzone offset
            tz = pytz.timezone(user.birth_tz)
            dt = datetime.datetime.combine(user.birth_date, datetime.time(h, m))
            offset = tz.utcoffset(dt).total_seconds() / 3600.0

            api_data = await client.get_western_horoscope(
                day=user.birth_date.day,
                month=user.birth_date.month,
                year=user.birth_date.year,
                hour=h,
                minute=m,
                lat=user.birth_lat,
                lon=user.birth_lon,
                tzone=offset
            )
            
            natal.api_raw_json = api_data
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(natal, "api_raw_json")
            await db.flush()
            logger.info(f"Level 1 Enrichment (API) successful for natal_id {natal_id}")
            
        except Exception as e:
            logger.error(f"Level 1 Enrichment failed for natal_id {natal_id}: {e}")
            # We don't raise here to allow the rest of the pipeline to run even if API fails
