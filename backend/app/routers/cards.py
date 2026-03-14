"""
Cards router: get all 264 cards with statuses, get single card detail.
"""
import json
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import CardProgress, AlignSession, SyncSession
from app.core.economy import hawkins_to_rank, RANK_NAMES

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "archetypes.json")) as f:
    ARCHETYPES = {item["id"]: item for item in json.load(f)}

with open(os.path.join(DATA_DIR, "spheres.json")) as f:
    SPHERES_DATA = {item["key"]: item for item in json.load(f)}

try:
    with open(os.path.join(DATA_DIR, "archetype_sphere_matrix.json"), "r", encoding="utf-8") as f:
        MATRIX_DATA = json.load(f)
except Exception:
    MATRIX_DATA = {}


class CardSummary(BaseModel):
    id: int
    archetype_id: int
    sphere: str
    archetype_name: str
    sphere_name_ru: str
    status: str
    rank: int
    rank_name: str
    hawkins_current: int
    hawkins_peak: int
    is_recommended_astro: bool
    is_recommended_portrait: bool
    is_recommended_ai: bool
    ai_score: float
    astro_priority: Optional[str]
    sync_sessions_count: int
    align_sessions_count: int


class CardDetail(CardSummary):
    archetype_shadow: str
    archetype_light: str
    archetype_description: str
    sphere_main_question: str
    sphere_agent_style: str
    astro_reason: Optional[str]
    sphere_color: str


@router.get("/{user_id}", response_model=list[CardSummary])
async def get_all_cards(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all 176 cards for a user with their current status."""
    result = await db.execute(
        select(CardProgress)
        .where(CardProgress.user_id == user_id)
        .order_by(CardProgress.sphere, CardProgress.archetype_id)
    )
    cards = result.scalars().all()

    response = []
    for card in cards:
        archetype = ARCHETYPES.get(card.archetype_id, {})
        sphere = SPHERES_DATA.get(card.sphere, {})
        rank = hawkins_to_rank(card.hawkins_peak)

        response.append(CardSummary(
            id=card.id,
            archetype_id=card.archetype_id,
            sphere=card.sphere,
            archetype_name=archetype.get("name", ""),
            sphere_name_ru=sphere.get("name_ru", card.sphere),
            status=card.status,
            rank=rank,
            rank_name=RANK_NAMES.get(rank, "☆ Спящий"),
            hawkins_current=card.hawkins_current,
            hawkins_peak=card.hawkins_peak,
            is_recommended_astro=card.is_recommended_astro,
            is_recommended_portrait=card.is_recommended_portrait,
            is_recommended_ai=card.is_recommended_ai,
            ai_score=card.ai_score or 0.0,
            astro_priority=card.astro_priority,
            sync_sessions_count=card.sync_sessions_count,
            align_sessions_count=card.align_sessions_count,
        ))

    return response


@router.get("/{user_id}/card/{card_id}", response_model=CardDetail)
async def get_card_detail(
    user_id: int,
    card_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed view of a single card."""
    result = await db.execute(
        select(CardProgress).where(
            CardProgress.id == card_id,
            CardProgress.user_id == user_id,
        )
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    archetype = ARCHETYPES.get(card.archetype_id, {})
    sphere = SPHERES_DATA.get(card.sphere, {})
    rank = hawkins_to_rank(card.hawkins_peak)

    matrix_data = MATRIX_DATA.get(str(card.archetype_id), {}).get(card.sphere, {})
    
    return CardDetail(
        id=card.id,
        archetype_id=card.archetype_id,
        sphere=card.sphere,
        archetype_name=archetype.get("name", ""),
        sphere_name_ru=sphere.get("name_ru", card.sphere),
        status=card.status,
        rank=rank,
        rank_name=RANK_NAMES.get(rank, "☆ Спящий"),
        hawkins_current=card.hawkins_current,
        hawkins_peak=card.hawkins_peak,
        is_recommended_astro=card.is_recommended_astro,
        is_recommended_portrait=card.is_recommended_portrait,
        is_recommended_ai=card.is_recommended_ai,
        ai_score=card.ai_score or 0.0,
        astro_priority=card.astro_priority,
        sync_sessions_count=card.sync_sessions_count,
        align_sessions_count=card.align_sessions_count,
        archetype_shadow=matrix_data.get("core_shadow", archetype.get("shadow", "")),
        archetype_light=matrix_data.get("core_light", archetype.get("light", "")),
        archetype_description=matrix_data.get("core_description", archetype.get("description", "")),
        sphere_main_question=sphere.get("main_question", ""),
        sphere_agent_style=sphere.get("agent_style", ""),
        astro_reason=card.astro_reason,
        sphere_color=sphere.get("color", "#ffffff"),
    )


class StateHistoryItem(BaseModel):
    date: str
    score: int
    type: str

@router.get("/{user_id}/card/{card_id}/history", response_model=list[StateHistoryItem])
async def get_card_history(
    user_id: int,
    card_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the history of Hawkins scores for a card (sync + all alignments)."""
    # 1. Verify card belongs to user
    card_result = await db.execute(
        select(CardProgress).where(
            CardProgress.id == card_id,
            CardProgress.user_id == user_id,
        )
    )
    if not card_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Card not found")

    history = []

    # 2. Get Sync Session (Initial Activation)
    sync_result = await db.execute(
        select(SyncSession).where(
            SyncSession.card_progress_id == card_id,
            SyncSession.is_complete == True
        ).order_by(SyncSession.created_at.asc())
    )
    syncs = sync_result.scalars().all()
    for s in syncs:
        if s.hawkins_score > 0:
            history.append({
                "date": s.created_at.isoformat(),
                "score": s.hawkins_score,
                "type": "sync"
            })

    # 3. Get Align Sessions
    align_result = await db.execute(
        select(AlignSession).where(
            AlignSession.card_progress_id == card_id,
            AlignSession.is_complete == True
        ).order_by(AlignSession.created_at.asc())
    )
    aligns = align_result.scalars().all()
    for a in aligns:
        # We can add entry and peak/exit to make the graph more detailed
        if a.hawkins_entry > 0:
            # We add a slight negative time offset for the entry score so it renders before the exit
            entry_time = a.created_at.isoformat() 
            history.append({
                "date": entry_time,
                "score": a.hawkins_entry,
                "type": "align_start"
            })
        if a.hawkins_exit > 0:
            # The exit time is simulated as later
            # (In a real app, AlignSession could store updated_at)
            history.append({
                "date": a.updated_at.isoformat() if hasattr(a, 'updated_at') and a.updated_at else a.created_at.isoformat(),
                "score": a.hawkins_exit,
                "type": "align_end"
            })

    # Sort chronological
    history.sort(key=lambda x: x["date"])
    
    return history
