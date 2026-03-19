"""
Calc router: birth data input → natal chart calculation → 264 cards generation.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models import User, NatalChart, CardProgress
from app.models.card_progress import CardStatus
from app.core.astrology.natal_chart import (
    calculate_natal_chart, geocode_place, to_dict as chart_to_dict
)
from app.rro.ocean.hub import OceanService
from app.rro.astro.river import AstroRiver
from app.rro.astro.rain import AstroRain
import logging
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter()

SPHERES = [
    "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
    "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
    "EXPANSION", "STATUS", "VISION", "SPIRIT"
]
ARCHETYPE_IDS = list(range(22))  # 0-21


class BirthDataRequest(BaseModel):
    birth_date: str      # "1990-01-15"
    birth_time: str      # "14:30" or "00:00" if unknown
    birth_place: str     # "Москва, Россия"
    user_id: int         # internal user ID
    gender: Optional[str] = None # "male", "female", "other"


class CalcResponse(BaseModel):
    success: bool
    natal_chart: dict
    total_cards: int
    message: str


class GeocodeRequest(BaseModel):
    birth_place: str

@router.post("/geocode")
async def get_geocode(request: GeocodeRequest):
    """Geocode a place name for confirmation."""
    try:
        lat, lon, tz_name = await geocode_place(request.birth_place)
        return {"lat": lat, "lon": lon, "tz_name": tz_name, "place": request.birth_place}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("", response_model=CalcResponse)
async def calculate(
    request: BirthDataRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Full calculation flow:
    1. Geocode birth place
    2. Calculate natal chart (pyswisseph)
    3. Calculate aspects
    4. Prioritize cards
    5. Create/update 264 CardProgress rows
    6. Save NatalChart to DB
    """
    logger.info(f"--- Astro Calculation Started for user {request.user_id} ---")
    # Get user
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        logger.error(f"User {request.user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    try:
        logger.info(f"Geocoding: {request.birth_place}")
        # Geocode
        lat, lon, tz_name = await geocode_place(request.birth_place)
        logger.info(f"Geocoding result: {lat}, {lon}, {tz_name}")
    except ValueError as e:
        logger.error(f"Geocoding failed for {request.birth_place}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Parse date
    birth_date = datetime.strptime(request.birth_date, "%Y-%m-%d")
    logger.info(f"Parsed birth date: {birth_date}")

    try:
        # 5. Level 1: Rain (Calculation & Persistence)
        natal = await AstroRain.process_onboarding(
            db=db,
            user_obj=user,
            birth_date=birth_date,
            birth_time=request.birth_time,
            lat=lat,
            lon=lon,
            tz_name=tz_name,
            location_name=request.birth_place
        )
        
        # 6. Finalize Level 1 (Rain) results and initiate Pipeline
        logger.info(f"Committing Level 1 (Rain) results for user {user.id}...")
        await db.commit()
        logger.info("Commit successful.")

        background_tasks.add_task(run_rro_pipeline, user.id, natal.id)

        return CalcResponse(
            success=True,
            natal_chart=natal.planets_json,
            total_cards=22 * 12,
            message=f"Карта рассчитана (L1). Синтез (L2/L3) запущен в фоне.",
        )
    except Exception as e:
        logger.error(f"Astro processing failed for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Astro processing error: {str(e)}"
        )

async def run_rro_pipeline(u_id: int, n_id: int):
    """
    Background RRO Pipeline executor.
    """
    logger.info(f"--- [BACKGROUND] RRO v2 Pipeline INITIALIZED for user {u_id} ---")
    try:
        async with AsyncSessionLocal() as session:
            # Get L1 data
            n_res = await session.execute(select(NatalChart).where(NatalChart.id == n_id))
            natal_obj = n_res.scalar_one_or_none()
            
            if not natal_obj:
                logger.error(f"[BACKGROUND] NatalChart {n_id} not found for user {u_id}")
                return

            # Level 1 Enrichment: Fetch and store API data
            logger.info(f"[BACKGROUND] Starting Level 1 (Rain API) for user {u_id}")
            await AstroRain.enrich_with_api(session, n_id)
            await session.refresh(natal_obj) # Ensure we have the api_raw_json

            # Level 2: River (Interpretation)
            logger.info(f"[BACKGROUND] Starting Level 2 (River) for user {u_id}")
            river = AstroRiver()
            interpretation_data = await river.flow(session, u_id, natal_obj)
            logger.info(f"[BACKGROUND] Level 2 (River) completed for user {u_id}")
            
            if interpretation_data:
                # Level 3: Ocean (Synthesis)
                logger.info(f"[BACKGROUND] Starting Level 3 (Ocean) for user {u_id}")
                await OceanService.update_ocean(session, u_id)
                await session.commit()
                logger.info(f"[BACKGROUND] RRO v2 Pipeline completed successfully for user {u_id}")

                # Notify user via Telegram
                user_res = await session.execute(select(User).where(User.id == u_id))
                user_obj = user_res.scalar_one_or_none()
                if user_obj and user_obj.tg_id:
                    msg = (
                        "✅ <b>Твой AVATAR обновлен!</b>\n\n"
                        "Глубинный синтез всех 12 сфер завершен. Полный психологический паспорт "
                        "и новые рекомендации уже ждут тебя в приложении. ✨"
                    )
                    await NotificationService.send_tg_message(user_obj.tg_id, msg)
            else:
                logger.warning(f"[BACKGROUND] Level 2 (River) returned no data for user {u_id}")
    except Exception as e:
        logger.error(f"[BACKGROUND] RRO v2 Pipeline failed for user {u_id}: {e}", exc_info=True)
