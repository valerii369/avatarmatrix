"""
Calc router: birth data input → natal chart calculation → 176 cards generation.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, NatalChart, CardProgress
from app.models.card_progress import CardStatus
from app.core.astrology.natal_chart import (
    calculate_natal_chart, geocode_place, to_dict as chart_to_dict
)
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
from app.core.astrology.priority_engine import generate_recommended_cards, to_dict as cards_to_dict

router = APIRouter()

SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]
ARCHETYPE_IDS = list(range(22))  # 0-21


class BirthDataRequest(BaseModel):
    birth_date: str      # "1990-01-15"
    birth_time: str      # "14:30" or "00:00" if unknown
    birth_place: str     # "Москва, Россия"
    user_id: int         # internal user ID


class CalcResponse(BaseModel):
    success: bool
    natal_chart: dict
    recommended_cards: list[dict]
    total_cards: int
    message: str


@router.post("", response_model=CalcResponse)
async def calculate(
    request: BirthDataRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Full calculation flow:
    1. Geocode birth place
    2. Calculate natal chart (pyswisseph)
    3. Calculate aspects
    4. Prioritize cards
    5. Create/update 176 CardProgress rows
    6. Save NatalChart to DB
    """
    # Get user
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Geocode
        lat, lon, tz_name = await geocode_place(request.birth_place)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Parse date
    birth_date = datetime.strptime(request.birth_date, "%Y-%m-%d")

    try:
        # Calculate natal chart
        chart = calculate_natal_chart(birth_date, request.birth_time, lat, lon, tz_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart calculation error: {e}")

    chart_dict = chart_to_dict(chart)

    # Calculate aspects
    aspects = calculate_aspects(chart_dict["planets"])
    aspects_dict = aspects_to_dict(aspects)

    # Generate recommended cards
    recommended_astro = generate_recommended_cards(chart)
    recommended_dict = cards_to_dict(recommended_astro)

    # Build set of recommended (archetype_id, sphere)
    recommended_set = {
        (r.archetype_id, r.sphere): r
        for r in recommended_astro
    }

    # Create/update 176 CardProgress rows
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
        natal.ascendant_sign = chart.ascendant_sign
        natal.ascendant_ruler = chart.ascendant_ruler
    else:
        natal = NatalChart(
            user_id=user.id,
            planets_json=chart_dict,
            aspects_json=aspects_dict,
            recommended_cards_json=recommended_dict,
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
    user.onboarding_done = True
    db.add(user)

    await db.commit()

    return CalcResponse(
        success=True,
        natal_chart=chart_dict,
        recommended_cards=recommended_dict,
        total_cards=22 * 8,
        message=f"Карта рассчитана. Рекомендовано {len(recommended_dict)} карточек.",
    )
