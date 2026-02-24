"""
Sync router: manage 10-phase synchronization sessions.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import CardProgress, SyncSession, User
from app.models.card_progress import CardStatus
from app.agents.master_agent import sync_phase_response, extract_sync_insights, evaluate_hawkins
from app.core.economy import award_energy, spend_energy, hawkins_to_rank, RANK_NAMES, calculate_xp_for_level
from app.core.portrait_builder import build_portrait_for_sphere
from app.database import AsyncSessionLocal

router = APIRouter()


async def _rebuild_sphere_portrait(user_id: int, sphere: str) -> None:
    """Background task: rebuild portrait for one sphere with its own DB session."""
    async with AsyncSessionLocal() as session:
        try:
            await build_portrait_for_sphere(session, user_id, sphere)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Portrait rebuild error: {e}")


class StartSyncRequest(BaseModel):
    user_id: int
    card_progress_id: int


class PhaseRequest(BaseModel):
    user_id: int
    sync_session_id: int
    phase: int
    user_response: Optional[str] = None


class SyncStatusResponse(BaseModel):
    session_id: int
    current_phase: int
    is_complete: bool
    phase_content: str
    phase_data: dict


@router.post("/start")
async def start_sync(
    request: StartSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a new synchronization session for a card."""
    # Get card
    card_result = await db.execute(
        select(CardProgress).where(
            CardProgress.id == request.card_progress_id,
            CardProgress.user_id == request.user_id,
        )
    )
    card = card_result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Get user
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()

    # Check energy
    can_spend = await spend_energy(db, user, "sync")
    if not can_spend:
        raise HTTPException(status_code=402, detail="Недостаточно ✦ Энергии")

    # Create sync session
    session = SyncSession(
        user_id=request.user_id,
        card_progress_id=request.card_progress_id,
        archetype_id=card.archetype_id,
        sphere=card.sphere,
        current_phase=1,
        phase_data={},
    )
    db.add(session)

    # Update card status
    card.status = CardStatus.IN_SYNC
    db.add(card)

    await db.commit()
    await db.refresh(session)

    # Generate Phase 1 content (no user input needed)
    phase_content = await sync_phase_response(
        phase=1,
        archetype_id=card.archetype_id,
        sphere=card.sphere,
        previous_phases={},
    )

    # Store phase 1 content
    session.phase_data = {"1": {"ai_content": phase_content, "user_response": None}}
    db.add(session)
    await db.commit()

    return {
        "session_id": session.id,
        "current_phase": 1,
        "is_complete": False,
        "phase_content": phase_content,
    }


@router.post("/phase")
async def process_phase(
    request: PhaseRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Process user response to a phase and generate next phase."""
    session_result = await db.execute(
        select(SyncSession).where(
            SyncSession.id == request.sync_session_id,
            SyncSession.user_id == request.user_id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_complete:
        raise HTTPException(status_code=400, detail="Session already complete")

    # Store user response for current phase
    phase_data = dict(session.phase_data or {})
    phase_key = str(request.phase)
    if phase_key not in phase_data:
        phase_data[phase_key] = {}
    phase_data[phase_key]["user_response"] = request.user_response

    # Evaluate Hawkins for this phase's response
    if request.user_response:
        hawkins_eval = await evaluate_hawkins(request.user_response)
        phase_data[phase_key]["hawkins_eval"] = hawkins_eval

    # Check if this is the last phase
    if request.phase >= 10:
        # Complete the session
        insights = await extract_sync_insights(phase_data, session.archetype_id, session.sphere)

        session.phase_data = phase_data
        session.is_complete = True
        session.hawkins_score = insights.get("hawkins_score", 100)
        session.hawkins_level = insights.get("hawkins_level", "Страх")
        session.extracted_core_belief = insights.get("core_belief", "")
        session.extracted_shadow_pattern = insights.get("shadow_pattern", "")
        session.extracted_body_anchor = insights.get("body_anchor", "")
        session.extracted_projection = insights.get("projection", "")
        session.extracted_avoidance = insights.get("avoidance", "")
        session.extracted_dominant_emotion = insights.get("dominant_emotion", "")
        session.extracted_tags = insights.get("tags", [])
        db.add(session)

        # Update card progress
        card_result = await db.execute(
            select(CardProgress).where(CardProgress.id == session.card_progress_id)
        )
        card = card_result.scalar_one_or_none()
        if card:
            card.status = CardStatus.SYNCED
            card.hawkins_current = session.hawkins_score
            if session.hawkins_score > card.hawkins_peak:
                card.hawkins_peak = session.hawkins_score
            card.hawkins_entry = session.hawkins_score
            card.sync_sessions_count += 1
            db.add(card)

        # Update card rank
        if card:
            new_rank = hawkins_to_rank(card.hawkins_peak)
            if new_rank > card.rank:
                card.rank = new_rank
                card.rank_name = RANK_NAMES[new_rank]
                await award_energy(db, user, "card_rank_up") if user else None
            db.add(card)

        # Award XP to user
        if user:
            xp_gained = insights.get("hawkins_score", 0) or 0
            user.xp = (user.xp or 0) + xp_gained
            # Level up?
            while user.evolution_level < 100 and user.xp >= calculate_xp_for_level(user.evolution_level + 1):
                user.evolution_level += 1
            db.add(user)
            await award_energy(db, user, "diary_entry")

        await db.commit()

        # Trigger portrait rebuild in background
        if card:
            background_tasks.add_task(
                _rebuild_sphere_portrait, request.user_id, session.sphere
            )

        return {
            "session_id": session.id,
            "current_phase": 10,
            "is_complete": True,
            "phase_content": f"Синхронизация завершена. Ваш уровень: {session.hawkins_level} ({session.hawkins_score}).\n\nЯдро-убеждение: {insights.get('core_belief', '')}",
            "insights": insights,
        }

    # Generate next phase
    next_phase = request.phase + 1
    next_content = await sync_phase_response(
        phase=next_phase,
        archetype_id=session.archetype_id,
        sphere=session.sphere,
        previous_phases=phase_data,
        user_message=request.user_response,
    )

    phase_data[str(next_phase)] = {"ai_content": next_content, "user_response": None}
    session.phase_data = phase_data
    session.current_phase = next_phase
    db.add(session)
    await db.commit()

    return {
        "session_id": session.id,
        "current_phase": next_phase,
        "is_complete": False,
        "phase_content": next_content,
    }
