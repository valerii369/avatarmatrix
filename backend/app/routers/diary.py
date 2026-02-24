from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import DiaryEntry, User
from app.core.economy import award_energy

router = APIRouter()


class DiaryCreateRequest(BaseModel):
    user_id: int
    archetype_id: int
    sphere: str
    content: Optional[str] = None
    voice_url: Optional[str] = None
    voice_transcript: Optional[str] = None
    integration_plan: Optional[str] = None
    align_session_id: Optional[int] = None
    entry_type: str = "manual"


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

    entry = DiaryEntry(
        user_id=request.user_id,
        archetype_id=request.archetype_id,
        sphere=request.sphere,
        content=request.content,
        voice_url=request.voice_url,
        voice_transcript=request.voice_transcript,
        integration_plan=request.integration_plan,
        align_session_id=request.align_session_id,
        entry_type=request.entry_type,
    )
    db.add(entry)
    await award_energy(db, user, "diary_entry")
    await db.commit()
    await db.refresh(entry)
    return {"id": entry.id, "message": "+10 ✦ за запись в дневник"}


@router.get("/{user_id}")
async def get_diary(user_id: int, sphere: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(DiaryEntry).where(DiaryEntry.user_id == user_id)
    if sphere:
        query = query.where(DiaryEntry.sphere == sphere)
    query = query.order_by(desc(DiaryEntry.created_at))
    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "archetype_id": e.archetype_id,
            "sphere": e.sphere,
            "content": e.content,
            "integration_plan": e.integration_plan,
            "integration_done": e.integration_done,
            "entry_type": e.entry_type,
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
            await award_energy(db, user, "integration_done")

    await db.commit()
    return {"message": "+20 ✦ за интеграцию" if request.done else "Отмечено частично"}
