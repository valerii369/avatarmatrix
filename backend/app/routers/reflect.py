from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date

from app.database import get_db
from app.models import User, DailyReflect
from app.core.economy import award_energy
from app.agents.master_agent import evaluate_hawkins

router = APIRouter()


class ReflectRequest(BaseModel):
    user_id: int
    current_emotion: str
    integration_done: str  # "yes", "no", "partial"
    focus_sphere: str


@router.post("")
async def daily_reflection(request: ReflectRequest, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()

    # Check if already done today
    existing = await db.execute(
        select(DailyReflect).where(
            DailyReflect.user_id == request.user_id,
            DailyReflect.reflect_date == today,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Рефлексия уже пройдена сегодня", "energy_awarded": 0}

    # Evaluate emotion → Hawkins
    hawkins_eval = await evaluate_hawkins(request.current_emotion)
    hawkins_today = hawkins_eval.get("score", 100)

    reflect = DailyReflect(
        user_id=request.user_id,
        reflect_date=today,
        current_emotion=request.current_emotion,
        hawkins_today=hawkins_today,
        integration_done=request.integration_done,
        focus_sphere=request.focus_sphere,
        energy_awarded=10,
    )
    db.add(reflect)

    await award_energy(db, user, "daily_reflection")
    await db.commit()

    return {
        "message": "+10 ✦ за ежедневную рефлексию",
        "energy_awarded": 10,
        "hawkins_today": hawkins_today,
        "hawkins_level": hawkins_eval.get("level", ""),
    }
