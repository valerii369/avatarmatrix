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
    recommended_cards: list
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

        background_tasks.add_task(
            run_dsb_pipeline, 
            user.id, 
            request.birth_date, 
            request.birth_time, 
            lat, 
            lon, 
            request.birth_place, 
            request.gender, # Optional full_name mapping
            AsyncSessionLocal
        )

        return CalcResponse(
            success=True,
            natal_chart=natal.planets_json,
            recommended_cards=natal.recommended_cards_json,
            total_cards=22 * 12,
            message=f"Карта рассчитана (L1). Синтез (L2/L3) запущен в фоне.",
        )
    except Exception as e:
        logger.error(f"Astro processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Astro processing error: {e}")

async def run_dsb_pipeline(u_id: int, birth_date, birth_time, lat, lon, place, full_name, session_maker):
    """
    Background DSB Pipeline executor.
    """
    logger.info(f"--- [BACKGROUND] DSB Pipeline INITIALIZED for user {u_id} ---")
    try:
        async with session_maker() as session:
            
            from app.dsb.calculators.base import BirthData
            from app.dsb.pipeline.orchestrator import PortraitOrchestrator
            
            birth_data = BirthData(
                date=birth_date,
                time=birth_time,
                place=place,
                lat=lat,
                lon=lon,
                timezone="UTC", # Not strictly needed as geocoding info is mixed, but passing 
                full_name=full_name
            )
            
            orchestrator = PortraitOrchestrator()
            await orchestrator.generate(birth_data, u_id, session)

    except Exception as e:
        logger.error(f"[BACKGROUND] DSB Pipeline failed for user {u_id}: {e}", exc_info=True)
