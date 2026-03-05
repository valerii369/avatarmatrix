from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import DiaryEntry, User
from app.core.economy import award_xp, XP_VALUES
from app.agents.master_agent import analyze_reflection, ARCHETYPES

router = APIRouter()


class DiaryCreateRequest(BaseModel):
    user_id: int
    archetype_id: Optional[int] = None
    sphere: Optional[str] = None
    content: Optional[str] = None
    voice_url: Optional[str] = None
    voice_transcript: Optional[str] = None
    integration_plan: Optional[str] = None
    align_session_id: Optional[int] = None
    entry_type: str = "manual" # session_result | manual | voice | reflection
    hawkins_score: Optional[int] = None
    ai_analysis: Optional[str] = None


class IntegrationUpdateRequest(BaseModel):
    user_id: int
    entry_id: int
    done: bool
    partial: bool = False


@router.post("")
async def create_entry(request: DiaryCreateRequest, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    h_score = request.hawkins_score
    ai_feedback = request.ai_analysis
    sphere = request.sphere
    arch_id = request.archetype_id

    # If it's a reflection and we don't have analysis, run it
    if request.entry_type == "reflection" and not ai_feedback:
        text_to_analyze = request.content or request.voice_transcript or ""
        if text_to_analyze:
            analysis = await analyze_reflection(text_to_analyze)
            h_score = analysis.get("hawkins_score", h_score)
            ai_feedback = analysis.get("ai_analysis", ai_feedback)
            sphere = analysis.get("sphere", sphere)
            arch_id = analysis.get("archetype_id", arch_id)

    entry = DiaryEntry(
        user_id=request.user_id,
        archetype_id=arch_id,
        sphere=sphere,
        content=request.content,
        voice_url=request.voice_url,
        voice_transcript=request.voice_transcript,
        integration_plan=request.integration_plan,
        align_session_id=request.align_session_id,
        entry_type=request.entry_type,
        hawkins_score=h_score,
        ai_analysis=ai_feedback,
    )
    db.add(entry)
    
    # Award energy/xp based on type
    bonus = "diary_entry"
    xp_bonus = XP_VALUES["diary_entry"]
    if request.entry_type == "reflection":
        bonus = "daily_reflection"
        xp_bonus = 20 # custom for reflection
    # Energy awards disabled per new tokenomics
    # await award_energy(db, user, bonus)
    await award_xp(db, user, xp_bonus)
    
    await db.commit()
    await db.refresh(entry)
    return {
        "id": entry.id, 
        "message": f"+{xp_bonus} XP за запись в дневник",
        "analysis": {
            "hawkins_score": h_score,
            "ai_analysis": ai_feedback,
            "sphere": sphere,
            "archetype_id": arch_id
        }
    }


@router.get("/{user_id}")
async def get_diary(
    user_id: int, 
    sphere: Optional[str] = None, 
    entry_type: Optional[str] = None,
    exclude_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(DiaryEntry).where(DiaryEntry.user_id == user_id)
    if sphere:
        query = query.where(DiaryEntry.sphere == sphere)
    if entry_type:
        query = query.where(DiaryEntry.entry_type == entry_type)
    if exclude_type:
        query = query.where(DiaryEntry.entry_type != exclude_type)
    
    query = query.order_by(desc(DiaryEntry.created_at))
    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "archetype_id": e.archetype_id,
            "archetype_name": ARCHETYPES.get(e.archetype_id, {}).get("name") if e.archetype_id else None,
            "sphere": e.sphere,
            "content": e.content,
            "integration_plan": e.integration_plan,
            "integration_done": e.integration_done,
            "entry_type": e.entry_type,
            "hawkins_score": e.hawkins_score,
            "ai_analysis": e.ai_analysis,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.post("/integration")
async def update_integration(request: IntegrationUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DiaryEntry).where(DiaryEntry.id == request.entry_id, DiaryEntry.user_id == request.user_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.integration_done = request.done
    entry.integration_done_partially = request.partial
    db.add(entry)

    if request.done:
        user_result = await db.execute(select(User).where(User.id == request.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            # await award_energy(db, user, "integration_done") # Disabled
            await award_xp(db, user, XP_VALUES["integration_success"])
    else:
        # User explicitly marked as NOT done (failure/partial)
        user_result = await db.execute(select(User).where(User.id == request.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            await award_xp(db, user, XP_VALUES["integration_failure"])

    await db.commit()
    return {"message": "Запись об интеграции обновлена"}
