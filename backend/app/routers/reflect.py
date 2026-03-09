from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from app.database import get_db
from app.models import User, DiaryEntry, CardProgress
from app.models.card_progress import CardStatus
from app.core.economy import spend_energy, award_xp
from app.agents.master_agent import analyze_reflection
from app.core.astrology.vector_matcher import match_text_to_archetypes

router = APIRouter()


class ReflectRequest(BaseModel):
    user_id: int
    content: str
    is_voice: bool = False
    use_ai: bool = True  # Default to True for backward compatibility, but UI will toggle


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

    # Branching logic based on use_ai
    analysis = {}
    h_score = 200
    ai_feedback = ""
    sphere = "IDENTITY"
    arch_id = 0
    discovered_cards = []
    energy_msg = "Запись сохранена в дневник"

    if request.use_ai:
        # Check energy (cost: 15 ✦)
        can_spend = await spend_energy(db, user, "reflection")
        if not can_spend:
            raise HTTPException(status_code=402, detail="Недостаточно ✦ Энергии (15✦ для рефлексии)")
        
        # Run AI Analysis
        analysis = await analyze_reflection(request.content)
        h_score = analysis.get("hawkins_score", 200)
        ai_feedback = analysis.get("ai_analysis", "")
        sphere = analysis.get("sphere", "IDENTITY")
        arch_id = analysis.get("archetype_id", 0)
        energy_msg = "-15 ✦ за глубокую рефлексию"

        # AI Card Accumulation & Discovery
        matches = await match_text_to_archetypes(db, request.content, top_k=5)
        new_recommendations_count = 0
        
        for arch_id_match, sphere_match, score_match in matches:
            cp_stmt = select(CardProgress).where(
                CardProgress.user_id == request.user_id,
                CardProgress.archetype_id == arch_id_match,
                CardProgress.sphere == sphere_match
            )
            cp_res = await db.execute(cp_stmt)
            cp = cp_res.scalar_one_or_none()
            if not cp:
                cp = CardProgress(user_id=request.user_id, archetype_id=arch_id_match, sphere=sphere_match, status=CardStatus.LOCKED, ai_score=0.0)
                db.add(cp)
            
            increment = score_match * 0.3
            cp.ai_score = min(2.0, cp.ai_score + increment)
            
            if cp.ai_score >= 1.0 and cp.status == CardStatus.LOCKED and new_recommendations_count < 2:
                cp.status = CardStatus.RECOMMENDED
                cp.is_recommended_ai = True
                new_recommendations_count += 1
                discovered_cards.append({"archetype_id": arch_id_match, "sphere": sphere_match, "ai_score": cp.ai_score})
        
        await award_xp(db, user, 25) # Higher bonus for AI reflection
    else:
        # Free diary entry - minimal XP, no energy cost, no discovery
        await award_xp(db, user, 10)

    # Save to DiaryEntry
    entry = DiaryEntry(
        user_id=request.user_id,
        archetype_id=arch_id,
        sphere=sphere,
        content=request.content,
        entry_type="reflection",
        hawkins_score=h_score if request.use_ai else None,
        ai_analysis=ai_feedback if request.use_ai else None,
    )
    db.add(entry)
    await db.commit()

    return {
        "message": energy_msg,
        "energy_awarded": 0,
        "discovered_cards": discovered_cards,
        "analysis": {
            "hawkins_score": h_score if request.use_ai else None,
            "hawkins_level": analysis.get("hawkins_level", "") if request.use_ai else "Diary",
            "ai_analysis": ai_feedback,
            "sphere": sphere
        }
    }
