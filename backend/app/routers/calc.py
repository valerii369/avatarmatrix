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
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
from app.core.astrology.llm_engine import synthesize_sphere_descriptions
from app.core.astrology.vector_matcher import match_archetypes_to_spheres
from app.core.user_print_manager import OceanService
import logging

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
        # Calculate natal chart
        logger.info("Calculating natal chart...")
        chart = calculate_natal_chart(birth_date, request.birth_time, lat, lon, tz_name)
        logger.info("Chart calculated successfully.")
    except Exception as e:
        logger.error(f"Chart calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"Chart calculation error: {e}")

    chart_dict = chart_to_dict(chart)

    # Calculate aspects
    logger.info("Calculating aspects...")
    aspects = calculate_aspects(chart_dict["planets"])
    aspects_dict = aspects_to_dict(aspects)
    logger.info(f"Aspects calculated: {len(aspects)} found.")

    # Rule-based recommendations (Standard Astro Logic)
    from app.core.astrology.priority_engine import generate_recommended_cards
    logger.info("Generating rule-based recommended cards...")
    recommended_rules = generate_recommended_cards(chart, aspects)
    logger.info(f"Rule-based recommendations: {len(recommended_rules)}")

    # Generate Synthesized Description via LLM
    logger.info("Synthesizing sphere descriptions via LLM...")
    sphere_descriptions = await synthesize_sphere_descriptions(chart_dict, aspects_dict)
    logger.info(f"LLM synthesis finished. Spheres: {list(sphere_descriptions.keys())}")
    
    # Generate recommended cards via Vector matching
    logger.info("Matching archetypes to spheres (vector search)...")
    recommended_vector = await match_archetypes_to_spheres(db, sphere_descriptions)
    logger.info(f"Vector search finished. Recommended (vector): {len(recommended_vector)}")
    
    # Merge Recommendations
    # Rules provide "ground truth" and specific reasons, Vectors provide "semantic fit"
    combined_recommendations = []
    seen_rec = set() # (archetype_id, sphere)

    # 1. Rule-based recommendations (Higher Priority for specific reasons)
    for r in recommended_rules:
        combined_recommendations.append(r)
        seen_rec.add((r.archetype_id, r.sphere))

    # 2. Vector-based recommendations (Fill the gaps)
    for r in recommended_vector:
        if (r.archetype_id, r.sphere) not in seen_rec:
            combined_recommendations.append(r)
            seen_rec.add((r.archetype_id, r.sphere))
    
    # Helper to convert to dict
    def cards_to_dict(cards):
        return [
            {
                "archetype_id": c.archetype_id,
                "sphere": c.sphere,
                "priority": c.priority,
                "reason": c.reason,
            }
            for c in cards
        ]
        
    recommended_dict = cards_to_dict(combined_recommendations)

    # Build set of recommended for CardProgress
    recommended_set = {
        (r.archetype_id, r.sphere): r
        for r in combined_recommendations
    }

    # Create/update 264 CardProgress rows
    existing_result = await db.execute(
        select(CardProgress).where(CardProgress.user_id == user.id)
    )
    existing_cards = {
        (cp.archetype_id, cp.sphere): cp
        for cp in existing_result.scalars().all()
    }

    for archetype_id in ARCHETYPE_IDS:
        for sphere in SPHERES:
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
                    user_id=user.id,
                    archetype_id=archetype_id,
                    sphere=sphere,
                    status=status,
                    is_recommended_astro=rec is not None,
                    astro_priority=rec.priority if rec else None,
                    astro_reason=rec.reason if rec else None,
                )
                db.add(cp)

    # Save/update NatalChart
    natal_result = await db.execute(select(NatalChart).where(NatalChart.user_id == user.id))
    natal = natal_result.scalar_one_or_none()

    if natal:
        natal.planets_json = chart_dict
        natal.aspects_json = aspects_dict
        natal.recommended_cards_json = recommended_dict
        natal.sphere_descriptions_json = sphere_descriptions
        natal.ascendant_sign = chart.ascendant_sign
        natal.ascendant_ruler = chart.ascendant_ruler
    else:
        natal = NatalChart(
            user_id=user.id,
            planets_json=chart_dict,
            aspects_json=aspects_dict,
            recommended_cards_json=recommended_dict,
            sphere_descriptions_json=sphere_descriptions,
            ascendant_sign=chart.ascendant_sign,
            ascendant_ruler=chart.ascendant_ruler,
        )
        db.add(natal)

    # Update user birth data
    user.birth_date = birth_date
    user.birth_time = request.birth_time
    user.birth_place = request.birth_place
    user.birth_lat = lat
    user.birth_lon = lon
    user.birth_tz = tz_name
    user.gender = request.gender
    user.onboarding_done = True
    db.add(user)

    # 7. Finalize Level 1 (Rain) results and initiate Pipeline
    logger.info(f"Committing Level 1 (Rain) results for user {user.id}...")
    await db.commit()
    logger.info("Commit successful.")

    # Level 2 & 3 Pipeline (Background)
    from app.services.astro_river import AstroRiver
    from app.database import AsyncSessionLocal

    async def _run_rro_pipeline(u_id, n_id):
        async with AsyncSessionLocal() as session:
            try:
                # Get L1 data
                n_res = await session.execute(select(NatalChart).where(NatalChart.id == n_id))
                natal_obj = n_res.scalar_one()

                # Level 2: River (Interpretation)
                river = AstroRiver()
                interpretation_data = await river.flow(session, u_id, natal_obj)
                
                if interpretation_data:
                    # Level 3: Ocean (Synthesis)
                    await OceanService.update_ocean(session, u_id, [interpretation_data])
                    await session.commit()
                    logger.info(f"RRO v2 Pipeline completed for user {u_id}")
            except Exception as e:
                logger.error(f"RRO v2 Pipeline failed for user {u_id}: {e}")

    background_tasks.add_task(_run_rro_pipeline, user.id, natal.id)

    return CalcResponse(
        success=True,
        natal_chart=chart_dict,
        recommended_cards=recommended_dict,
        total_cards=22 * 12,
        message=f"Карта рассчитана (L1). Синтез (L2/L3) запущен в фоне.",
    )
