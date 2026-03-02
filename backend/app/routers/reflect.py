from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date

from app.database import get_db
from app.models import User, DailyReflect, DiaryEntry
from app.core.economy import award_energy, award_xp, XP_VALUES
from app.agents.master_agent import analyze_reflection

router = APIRouter()


class ReflectRequest(BaseModel):
    user_id: int
    content: str  # New: supports long text / transcript
    is_voice: bool = False


@router.post("")
async def daily_reflection(request: ReflectRequest, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()

    # Check if a reflection was already done today in DiaryEntry
    existing = await db.execute(
        select(DiaryEntry).where(
            DiaryEntry.user_id == request.user_id,
            DiaryEntry.entry_type == "reflection",
            DiaryEntry.created_at >= today
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Рефлексия уже пройдена сегодня", "energy_awarded": 0}

    # Run AI Analysis
    analysis = await analyze_reflection(request.content)
    
    h_score = analysis.get("hawkins_score", 200)
    ai_feedback = analysis.get("ai_analysis", "")
    sphere = analysis.get("sphere", "IDENTITY")
    arch_id = analysis.get("archetype_id", 0)

    # Save to unified DiaryEntry
    entry = DiaryEntry(
        user_id=request.user_id,
        archetype_id=arch_id,
        sphere=sphere,
        content=request.content,
        entry_type="reflection",
        hawkins_score=h_score,
        ai_analysis=ai_feedback,
    )
    db.add(entry)

    await award_energy(db, user, "daily_reflection")
    await award_xp(db, user, 20) # Bonus for reflection
    await db.commit()

    return {
        "message": "+10 ✦ за ежедневную рефлексию",
        "energy_awarded": 10,
        "analysis": {
            "hawkins_score": h_score,
            "hawkins_level": analysis.get("hawkins_level", ""),
            "ai_analysis": ai_feedback,
            "sphere": sphere
        }
    }
