"""
Session router: WebSocket-based alignment sessions (6 stages).
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import CardProgress, AlignSession, SyncSession, User, DiaryEntry
from app.agents.align_agent import alignment_session_message, check_alignment_depth
from app.agents.hawkins_agent import evaluate_hawkins
from app.agents.analytic_agent import generate_alignment_summary, run_alignment_expert_analysis
from app.core.economy import spend_energy, hawkins_to_rank, process_card_rank_up
from app.config import settings

router = APIRouter()


@router.websocket("/{user_id}/{card_progress_id}")
async def alignment_session(
    websocket: WebSocket,
    user_id: int,
    card_progress_id: int,
):
    """
    WebSocket alignment session with optimized DB connection management.
    """
    await websocket.accept()

    # 1. INITIAL LOAD (Read context and create session record)
    async with AsyncSessionLocal() as db:
        # Load card
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
        can_spend = await spend_energy(db, user, "alignment")
        if not can_spend:
            await websocket.send_json({"type": "error", "content": "Недостаточно ✦ Энергии (20✦ для выравнивания)"})
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
        archetype_id = card.archetype_id
        sphere = card.sphere

        # Build History Context
        history_lines = []
        if last_sync:
            history_lines.append(f"--- СИНХРОНИЗАЦИЯ ({last_sync.created_at.strftime('%Y-%m-%d %H:%M')}) ---")
            history_lines.append(f"Итог: Хокинс {last_sync.hawkins_score} ({last_sync.hawkins_level})")
            history_lines.append(f"Ядро: {last_sync.extracted_core_belief}")
            history_lines.append(f"Тень: {last_sync.extracted_shadow_pattern}")
            if last_sync.session_transcript:
                history_lines.append("Диалог:")
                for m in last_sync.session_transcript[-6:]: 
                    history_lines.append(f"{m['role']}: {m['content']}")
        
        for idx, prev in enumerate(prev_aligns):
            history_lines.append(f"\n--- СЕССИЯ ВЫРАВНИВАНИЯ #{idx+1} ({prev.created_at.strftime('%Y-%m-%d %H:%M')}) ---")
            history_lines.append(f"Хокинс: вход {prev.hawkins_entry} -> пик {prev.hawkins_peak}")
            if prev.messages_json:
                history_lines.append("Диалог:")
                for m in prev.messages_json[-4:]: 
                    history_lines.append(f"{m.get('role')}: {m.get('content')}")
        
        history_context = "\n".join(history_lines)

        # Create session record
        align_session = AlignSession(
            user_id=user_id,
            card_progress_id=card_progress_id,
            archetype_id=archetype_id,
            sphere=sphere,
            hawkins_entry=hawkins_entry,
            hawkins_min=hawkins_entry,
            hawkins_peak=hawkins_entry,
            messages_json=[],
        )
        db.add(align_session)
        await db.commit()
        await db.refresh(align_session)
        align_session_id = align_session.id

    # 2. SESSION LOOP (Variables in memory)
    chat_history = []
    current_stage = 1
    hawkins_min = hawkins_entry
    hawkins_peak = hawkins_entry
    current_hawkins = hawkins_entry
    session_expert_results = {}

    # Initial AI message
    opening = await alignment_session_message(
        stage=1,
        archetype_id=archetype_id,
        sphere=sphere,
        hawkins_score=hawkins_entry,
        chat_history=[],
        user_message="Начало сессии",
        core_belief=core_belief,
        shadow_pattern=shadow_pattern,
        history_context=history_context,
    )
    chat_history.append({"role": "assistant", "content": opening})

    await websocket.send_json({
        "type": "opening",
        "content": opening,
        "protocol": 1,
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
                
                if user_content.strip():
                    depth_result = await check_alignment_depth(user_content)
                    is_sufficient = depth_result.get("is_sufficient", False)
                    chat_history.append({"role": "user", "content": user_content})

                    # Provide full history as context for more accurate assessment
                    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history[:-1]])
                    hawkins_eval = await evaluate_hawkins(user_content, context=history_str)
                    current_hawkins = hawkins_eval.get("score", current_hawkins)
                    hawkins_min = min(hawkins_min, current_hawkins)
                    hawkins_peak = max(hawkins_peak, current_hawkins)

                    if is_sufficient or stage_attempts >= 1 or is_manual_transition:
                        if current_stage < 3:
                            current_stage += 1
                            stage_attempts = 0
                    else:
                        is_deepening = True
                        stage_attempts += 1
                elif is_manual_transition:
                    if current_stage < 3:
                        current_stage += 1
                        stage_attempts = 0
                
                effective_user_content = user_content if user_content.strip() else "[Переход к следующему протоколу]"
                is_complete = current_stage >= 3 and (user_content.strip() or is_manual_transition) and not is_deepening

                ai_response = await alignment_session_message(
                    stage=current_stage,
                    archetype_id=archetype_id,
                    sphere=sphere,
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

                expert_results = {}
                if is_complete:
                    expert_results = await run_alignment_expert_analysis(
                        chat_history=chat_history,
                        archetype_id=archetype_id,
                        sphere=sphere
                    )
                    session_expert_results = expert_results

                await websocket.send_json({
                    "type": "response",
                    "content": ai_response,
                    "protocol": current_stage,
                    "hawkins_current": expert_results.get("hawkins_score") if is_complete else current_hawkins,
                    "hawkins_min": hawkins_min,
                    "hawkins_peak": hawkins_peak,
                    "is_complete": is_complete,
                    "is_deepening": is_deepening,
                    "expert_results": expert_results if is_complete else None
                })

                if is_complete:
                    break

            except WebSocketDisconnect:
                break
            except Exception:
                await websocket.send_json({"type": "error", "content": "Ошибка обработки сообщения"})

    except Exception:
        pass

    # 3. FINAL SAVE (Save all results and update stats)
    async with AsyncSessionLocal() as db:
        # Re-fetch session
        align_session = await db.get(AlignSession, align_session_id)
        if not align_session: return

        align_session.messages_json = chat_history
        align_session.stages_completed = current_stage
        align_session.is_complete = current_stage >= 3
        
        expert_results = session_expert_results
        if align_session.is_complete and expert_results:
            expert_score = expert_results.get("hawkins_score", hawkins_peak)
            align_session.hawkins_min = min(hawkins_min, expert_score)
            align_session.hawkins_peak = max(hawkins_peak, expert_score)
            align_session.hawkins_exit = expert_score
        else:
            align_session.hawkins_min = hawkins_min
            align_session.hawkins_peak = hawkins_peak
            align_session.hawkins_exit = current_hawkins
            
        # Re-fetch card and user
        card_result = await db.execute(select(CardProgress).where(CardProgress.id == card_progress_id))
        card = card_result.scalar_one_or_none()
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if card:
            final_core_score = expert_results.get("hawkins_score", current_hawkins)
            card.hawkins_current = final_core_score
            if final_core_score < card.hawkins_min:
                card.hawkins_min = final_core_score
            
            final_peak = max(hawkins_peak, expert_results.get("hawkins_score", 0))
            if final_peak > card.hawkins_peak:
                card.hawkins_peak = final_peak
                
            old_rank = card.rank
            new_rank = hawkins_to_rank(card.hawkins_peak)
            card.rank = new_rank
            
            if user and new_rank > old_rank:
                await process_card_rank_up(db, user, old_rank, new_rank, card.hawkins_peak)
            card.align_sessions_count += 1

        # Diary entry
        if align_session.is_complete and card:
            try:
                summary = await generate_alignment_summary(
                    chat_history=chat_history,
                    archetype_id=card.archetype_id,
                    sphere=card.sphere
                )
                align_session.new_belief = summary.get("new_belief")
                align_session.integration_plan = summary.get("integration_plan")
                
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
            except Exception:
                pass

        await db.commit()
