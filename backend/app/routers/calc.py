from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models import User, NatalChart
from app.core.astrology.natal_chart import geocode_place
from app.dsb.pipeline.orchestrator import PortraitOrchestrator
from app.dsb.calculators.base import BirthData
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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
    Pure DSB Onboarding Flow:
    1. Geocode
    2. DSB L1 (Synchronous) -> NatalChart & CardProgress Sync
    3. Return L1 results
    4. Trigger DSB L2/L3 (Background)
    """
    logger.info(f"--- [DSB] Onboarding Started for user {request.user_id} ---")
    
    # 1. Get user
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        logger.error(f"User {request.user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # 2. Geocoding
        lat, lon, tz_name = await geocode_place(request.birth_place)
        
        # 3. Prepare BirthData
        birth_date_obj = datetime.strptime(request.birth_date, "%Y-%m-%d").date()
        birth_time_obj = None
        if request.birth_time:
            try:
                birth_time_obj = datetime.strptime(request.birth_time, "%H:%M").time()
            except:
                birth_time_obj = datetime.strptime("12:00", "%H:%M").time()

        birth_data = BirthData(
            date=birth_date_obj,
            time=birth_time_obj,
            place=request.birth_place,
            lat=lat,
            lon=lon,
            timezone=tz_name,
            full_name=user.first_name
        )

        # 4. DSB L1 Initialization (Synchronous for fast UI)
        orchestrator = PortraitOrchestrator()
        dsb_res = await orchestrator.initialize_onboarding_layer(birth_data, user.id, db)
        
        if "error" in dsb_res:
            raise Exception(dsb_res["error"])

        # 5. Update User Object
        user.birth_date = birth_date_obj
        user.birth_time = request.birth_time
        user.birth_place = request.birth_place
        user.birth_lat = lat
        user.birth_lon = lon
        user.birth_tz = tz_name
        user.onboarding_done = True
        db.add(user)
        
        await db.commit()
        logger.info(f"DSB L1 Commit successful for user {user.id}")

        # 6. Trigger L2/L3 Background Pipeline
        background_tasks.add_task(
            run_dsb_pipeline, 
            user.id, 
            birth_data,
            AsyncSessionLocal
        )

        return CalcResponse(
            success=True,
            natal_chart=dsb_res["natal_chart"],
            recommended_cards=dsb_res["recommended_cards"],
            total_cards=22 * 12,
            message="Расчёт по системе DSB (L1) завершён. Идёт синтез 12 сфер (L2/L3) в фоне.",
        )

    except Exception as e:
        logger.error(f"DSB Onboarding failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Onboarding error: {e}")

async def run_dsb_pipeline(u_id: int, birth_data: BirthData, session_maker):
    """
    Background DSB Pipeline executor.
    """
    logger.info(f"--- [BACKGROUND] DSB Pipeline STARTED for user {u_id} ---")
    try:
        async with session_maker() as session:
            orchestrator = PortraitOrchestrator()
            await orchestrator.generate(birth_data, u_id, session)
    except Exception as e:
        logger.error(f"[BACKGROUND] DSB Pipeline failed for user {u_id}: {e}", exc_info=True)
