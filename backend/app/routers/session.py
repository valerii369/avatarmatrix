"""
Session router: WebSocket-based alignment sessions (6 stages).
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import CardProgress, AlignSession, SyncSession, User
from app.models.card_progress import CardStatus
from app.agents.master_agent import alignment_session_message, evaluate_hawkins
from app.core.economy import award_energy, spend_energy, hawkins_to_rank
from app.config import settings

router = APIRouter()


@router.websocket("/{user_id}/{card_progress_id}")
async def alignment_session(
    websocket: WebSocket,
    user_id: int,
    card_progress_id: int,
):
    """
    WebSocket alignment session.
    Client sends: {"type": "message", "content": "...", "stage": 1}
    Server sends: {"type": "response", "content": "...", "stage": 1, "is_complete": false}
    """
    await websocket.accept()

    async with AsyncSessionLocal() as db:
        # Load card and last sync session
        card_result = await db.execute(
            select(CardProgress).where(
                CardProgress.id == card_progress_id,
                CardProgress.user_id == user_id,
            )
        )
        card = card_result.scalar_one_or_none()
        if not card:
            await websocket.send_json({"type": "error", "content": "Card not found"})
            await websocket.close()
            return

        # Check energy
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        can_spend = await spend_energy(db, user, "deep_session")
        if not can_spend:
            await websocket.send_json({"type": "error", "content": "Недостаточно ✦ Энергии (40✦ для сессии)"})
            await websocket.close()
            return

        # Get sync session data (for context)
        sync_result = await db.execute(
            select(SyncSession).where(
                SyncSession.card_progress_id == card_progress_id,
                SyncSession.is_complete == True,
            ).order_by(SyncSession.created_at.desc())
        )
        last_sync = sync_result.scalar_one_or_none()

        core_belief = last_sync.extracted_core_belief if last_sync else ""
        shadow_pattern = last_sync.extracted_shadow_pattern if last_sync else ""
        hawkins_entry = card.hawkins_current or 100

        # Create align session
        align_session = AlignSession(
            user_id=user_id,
            card_progress_id=card_progress_id,
            archetype_id=card.archetype_id,
            sphere=card.sphere,
            hawkins_entry=hawkins_entry,
            hawkins_min=hawkins_entry,
            hawkins_peak=hawkins_entry,
            messages_json=[],
        )
        db.add(align_session)
        card.status = CardStatus.ALIGNING
        db.add(card)
        await db.commit()
        await db.refresh(align_session)

        chat_history = []
        current_stage = 1
        hawkins_min = hawkins_entry
        hawkins_peak = hawkins_entry

        # Send opening message
        opening = await alignment_session_message(
            stage=1,
            archetype_id=card.archetype_id,
            sphere=card.sphere,
            hawkins_score=hawkins_entry,
            chat_history=[],
            user_message="Начало сессии",
            core_belief=core_belief,
            shadow_pattern=shadow_pattern,
        )

        await websocket.send_json({
            "type": "opening",
            "content": opening,
            "stage": 1,
            "hawkins": hawkins_entry,
        })

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "message")
                user_content = data.get("content", "")
                requested_stage = data.get("stage", current_stage)

                if msg_type == "close":
                    break

                # Evaluate Hawkins from user message
                hawkins_eval = await evaluate_hawkins(user_content)
                current_hawkins = hawkins_eval.get("score", hawkins_entry)
                hawkins_min = min(hawkins_min, current_hawkins)
                hawkins_peak = max(hawkins_peak, current_hawkins)

                # Add to chat history
                chat_history.append({"role": "user", "content": user_content})

                # Generate AI response
                ai_response = await alignment_session_message(
                    stage=requested_stage,
                    archetype_id=card.archetype_id,
                    sphere=card.sphere,
                    hawkins_score=current_hawkins,
                    chat_history=chat_history,
                    user_message=user_content,
                    core_belief=core_belief,
                    shadow_pattern=shadow_pattern,
                    token_budget=settings.TOKEN_BUDGET_DEEP_SESSION,
                )

                chat_history.append({"role": "assistant", "content": ai_response})
                current_stage = requested_stage

                # Check if session complete (stage 6 done)
                is_complete = requested_stage >= 6 and msg_type == "complete_stage"

                await websocket.send_json({
                    "type": "response",
                    "content": ai_response,
                    "stage": current_stage,
                    "hawkins_current": current_hawkins,
                    "is_complete": is_complete,
                })

                if is_complete:
                    break

        except WebSocketDisconnect:
            pass

        # Save session results
        align_session.messages_json = chat_history
        align_session.hawkins_min = hawkins_min
        align_session.hawkins_peak = hawkins_peak
        align_session.hawkins_exit = hawkins_peak
        align_session.stages_completed = current_stage
        align_session.is_complete = current_stage >= 6
        db.add(align_session)

        # Update card progress
        card.status = CardStatus.ALIGNED if current_stage >= 6 else CardStatus.SYNCED
        card.hawkins_current = hawkins_peak
        if hawkins_peak > card.hawkins_peak:
            card.hawkins_peak = hawkins_peak
        new_rank = hawkins_to_rank(card.hawkins_peak)
        if new_rank > card.rank:
            card.rank = new_rank
            # XP for rank up
            user_result2 = await db.execute(select(User).where(User.id == user_id))
            user2 = user_result2.scalar_one_or_none()
            if user2:
                user2.xp += hawkins_peak
                await award_energy(db, user2, "card_rank_up")
        card.align_sessions_count += 1
        db.add(card)
        db.add(user)
        await db.commit()
