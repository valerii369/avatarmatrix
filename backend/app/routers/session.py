"""
Session router: WebSocket-based alignment sessions (6 stages).
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import CardProgress, AlignSession, SyncSession, User, DiaryEntry
from app.models.card_progress import CardStatus
from app.agents.master_agent import (
    alignment_session_message, 
    evaluate_hawkins, 
    generate_alignment_summary,
    run_alignment_expert_analysis,
    check_alignment_depth
)
from app.core.economy import award_energy, spend_energy, hawkins_to_rank, process_card_rank_up
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

        # Get all previous alignment sessions for this card
        align_history_result = await db.execute(
            select(AlignSession).where(
                AlignSession.card_progress_id == card_progress_id,
                AlignSession.is_complete == True
            ).order_by(AlignSession.created_at.asc())
        )
        prev_aligns = align_history_result.scalars().all()

        core_belief = last_sync.extracted_core_belief if last_sync else ""
        shadow_pattern = last_sync.extracted_shadow_pattern if last_sync else ""
        hawkins_entry = card.hawkins_current or 100

        # Build History Context
        history_lines = []
        if last_sync:
            history_lines.append(f"--- СИНХРОНИЗАЦИЯ ({last_sync.created_at.strftime('%Y-%m-%d %H:%M')}) ---")
            history_lines.append(f"Итог: Хокинс {last_sync.hawkins_score} ({last_sync.hawkins_level})")
            history_lines.append(f"Ядро: {last_sync.extracted_core_belief}")
            history_lines.append(f"Тень: {last_sync.extracted_shadow_pattern}")
            if last_sync.session_transcript:
                history_lines.append("Диалог:")
                for m in last_sync.session_transcript[-6:]: # Last 6 messages for brevity
                    history_lines.append(f"{m['role']}: {m['content']}")
        
        for idx, prev in enumerate(prev_aligns):
            history_lines.append(f"\n--- СЕССИЯ ВЫРАВНИВАНИЯ #{idx+1} ({prev.created_at.strftime('%Y-%m-%d %H:%M')}) ---")
            history_lines.append(f"Хокинс: вход {prev.hawkins_entry} -> пик {prev.hawkins_peak}")
            if prev.messages_json:
                history_lines.append("Диалог:")
                for m in prev.messages_json[-4:]: # Last 4 messages
                    history_lines.append(f"{m.get('role')}: {m.get('content')}")
        
        history_context = "\n".join(history_lines)

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
        # card.status = CardStatus.ALIGNING  # Keep it active
        # db.add(card)
        await db.commit()
        await db.refresh(align_session)

        chat_history = []
        current_stage = 1
        hawkins_min = hawkins_entry
        hawkins_peak = hawkins_entry
        current_hawkins = hawkins_entry

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
            history_context=history_context,
        )

        await websocket.send_json({
            "type": "opening",
            "content": opening,
            "stage": 1,
            "hawkins": hawkins_entry,
        })

        try:
            stage_attempts = 0
            while True:
                try:
                    data = await websocket.receive_json()
                    msg_type = data.get("type", "message")
                    user_content = data.get("content", "")
                    
                    if msg_type == "close":
                        break

                    is_manual_transition = (msg_type == "complete_stage")
                    is_deepening = False
                    
                    # Check depth if there is content
                    if user_content.strip():
                        depth_result = await check_alignment_depth(user_content)
                        is_sufficient = depth_result.get("is_sufficient", False)
                        
                        # Add to history
                        chat_history.append({"role": "user", "content": user_content})

                        # Evaluate Hawkins
                        hawkins_eval = await evaluate_hawkins(user_content)
                        current_hawkins = hawkins_eval.get("score", current_hawkins)
                        hawkins_min = min(hawkins_min, current_hawkins)
                        hawkins_peak = max(hawkins_peak, current_hawkins)

                        # Stage transition logic
                        if is_sufficient or stage_attempts >= 1 or is_manual_transition:
                            if current_stage < 6:
                                current_stage += 1
                                stage_attempts = 0
                        else:
                            is_deepening = True
                            stage_attempts += 1
                    elif is_manual_transition:
                        if current_stage < 6:
                            current_stage += 1
                            stage_attempts = 0
                    
                    effective_user_content = user_content if user_content.strip() else "[Переход к следующему этапу]"
                    
                    # Check if session is complete (after possible increment)
                    is_complete = current_stage >= 6 and (user_content.strip() or is_manual_transition) and not is_deepening

                    # Generate AI response
                    ai_response = await alignment_session_message(
                        stage=current_stage,
                        archetype_id=card.archetype_id,
                        sphere=card.sphere,
                        hawkins_score=int(current_hawkins),
                        chat_history=chat_history,
                        user_message=effective_user_content,
                        core_belief=core_belief,
                        shadow_pattern=shadow_pattern,
                        history_context=history_context,
                        token_budget=settings.TOKEN_BUDGET_DEEP_SESSION,
                        is_deepening=is_deepening
                    )
                    chat_history.append({"role": "assistant", "content": ai_response})

                    # Expert analysis for final stage
                    expert_results = {}
                    if is_complete:
                        expert_results = await run_alignment_expert_analysis(
                            chat_history=chat_history,
                            archetype_id=card.archetype_id,
                            sphere=card.sphere
                        )

                    await websocket.send_json({
                        "type": "response",
                        "content": ai_response,
                        "stage": current_stage,
                        "hawkins_current": expert_results.get("hawkins_score") if is_complete else current_hawkins,
                        "hawkins_min": hawkins_min,
                        "hawkins_peak": hawkins_peak,
                        "is_complete": is_complete,
                        "is_deepening": is_deepening,
                        "expert_results": expert_results if is_complete else None
                    })

                    if is_complete:
                        session_expert_results = expert_results
                        break
                except Exception as e:
                    print(f"Error in alignment loop: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "content": "Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте еще раз."
                    })
                    # We don't break here, allowing user to retry unless it's a critical failure

        except WebSocketDisconnect:
            pass

        # Save session results
        align_session.messages_json = chat_history
        align_session.stages_completed = current_stage
        align_session.is_complete = current_stage >= 6
        
        # 1. Use Expert Analysis results if available
        expert_results = session_expert_results if 'session_expert_results' in locals() else {}

        if align_session.is_complete and expert_results:
            expert_score = expert_results.get("hawkins_score", hawkins_peak)
            
            # Update session with expert results
            align_session.hawkins_min = min(hawkins_min, expert_score)
            align_session.hawkins_peak = max(hawkins_peak, expert_score)
            align_session.hawkins_exit = expert_score
        else:
            align_session.hawkins_min = hawkins_min
            align_session.hawkins_peak = hawkins_peak
            align_session.hawkins_exit = hawkins_peak
            
        db.add(align_session)

        # 2. Update card progress
        # If expert analysis was run, use it, otherwise use session tracking
        final_core_score = expert_results.get("hawkins_score", hawkins_min)
        card.hawkins_current = final_core_score
        
        if final_core_score < card.hawkins_min:
             card.hawkins_min = final_core_score
             
        # Peak is still tracked separately for record
        current_session_peak = expert_results.get("hawkins_score", hawkins_peak)
        if current_session_peak > card.hawkins_peak:
            card.hawkins_peak = current_session_peak
            
        old_rank = card.rank
        new_rank = hawkins_to_rank(card.hawkins_peak)
        card.rank = new_rank
        
        # XP and Energy for rank up
        if user and new_rank > old_rank:
            await process_card_rank_up(db, user, old_rank, new_rank, card.hawkins_peak)
        card.align_sessions_count += 1
        db.add(card)
        db.add(user)
        
        # Generation of Diary Entry
        if align_session.is_complete:
            try:
                summary = await generate_alignment_summary(
                    chat_history=chat_history,
                    archetype_id=card.archetype_id,
                    sphere=card.sphere
                )
                
                # Save summary to session
                align_session.new_belief = summary.get("new_belief")
                align_session.integration_plan = summary.get("integration_plan")
                db.add(align_session)
                
                # Create Diary Entry
                diary = DiaryEntry(
                    user_id=user_id,
                    align_session_id=align_session.id,
                    archetype_id=card.archetype_id,
                    sphere=card.sphere,
                    content=summary.get("final_insight") or "Итог сессии выравнивания",
                    integration_plan=summary.get("integration_plan"),
                    entry_type="session_result"
                )
                db.add(diary)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Diary generation error: {e}")

        await db.commit()
