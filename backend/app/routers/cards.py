"""
Cards router: get all 176 cards with statuses, get single card detail.
"""
import json
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import CardProgress, SyncSession, AlignSession
from app.core.economy import hawkins_to_rank, RANK_NAMES

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "archetypes.json")) as f:
    ARCHETYPES = {item["id"]: item for item in json.load(f)}

with open(os.path.join(DATA_DIR, "spheres.json")) as f:
    SPHERES_DATA = {item["key"]: item for item in json.load(f)}


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
        astro_priority=card.astro_priority,
        sync_sessions_count=card.sync_sessions_count,
        align_sessions_count=card.align_sessions_count,
        archetype_shadow=archetype.get("shadow", ""),
        archetype_light=archetype.get("light", ""),
        archetype_description=archetype.get("description", ""),
        sphere_main_question=sphere.get("main_question", ""),
        sphere_agent_style=sphere.get("agent_style", ""),
        astro_reason=card.astro_reason,
        sphere_color=sphere.get("color", "#ffffff"),
    )
