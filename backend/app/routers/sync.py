"""
Sync router: manage 10-phase synchronization sessions.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import CardProgress, SyncSession, User, SphereKnowledge, UserWorldKnowledge
from app.models.card_progress import CardStatus
from app.agents.master_agent import (
    run_avatar_layer, 
    run_mirror_analysis, 
    is_abstract_response, 
    evaluate_hawkins
)
from app.core.economy import award_energy, spend_energy, hawkins_to_rank, RANK_NAMES, calculate_xp_for_level
from app.core.portrait_builder import build_portrait_for_sphere
from app.database import AsyncSessionLocal
from sqlalchemy import func

router = APIRouter()


async def _aggregate_knowledge(user_id: int, sphere: str) -> None:
    """Background task: Aggregate Level 3 -> Level 2 -> Level 1."""
    async with AsyncSessionLocal() as session:
        try:
            # 1. Aggregate to Level 2 (Sphere)
            # Find all completed synced cards in this sphere
            results = await session.execute(
                select(SyncSession).where(
                    SyncSession.user_id == user_id,
                    SyncSession.sphere == sphere,
                    SyncSession.is_complete == True
                )
            )
            sessions = results.scalars().all()
            if not sessions:
                return

            # Simple aggregation logic: average Hawkins, collect patterns
            avg_hawkins = int(sum(s.hawkins_score for s in sessions) / len(sessions))
            patterns = [s.core_pattern for s in sessions if s.core_pattern]
            completed_archetypes = list(set(s.archetype_id for s in sessions))
            
            # Find or create SphereKnowledge
            sk_result = await session.execute(
                select(SphereKnowledge).where(
                    SphereKnowledge.user_id == user_id,
                    SphereKnowledge.sphere == sphere
                )
            )
            sk = sk_result.scalar_one_or_none()
            if not sk:
                sk = SphereKnowledge(user_id=user_id, sphere=sphere)
                session.add(sk)
            
            sk.sphere_picture = f"Сводная картина по {len(sessions)} архетипам."
            sk.sphere_pattern = " / ".join(patterns[:3])
            sk.sphere_hawkins = avg_hawkins
            sk.cards_completed = completed_archetypes
            
            # 2. Aggregate to Level 1 (World)
            # Find all sphere knowledges for this user
            sk_all_result = await session.execute(
                select(SphereKnowledge).where(SphereKnowledge.user_id == user_id)
            )
            sks = sk_all_result.scalars().all()
            
            if sks:
                world_avg_hawkins = int(sum(s.sphere_hawkins for s in sks) / len(sks))
                completed_spheres = [s.sphere for s in sks]
                
                wk_result = await session.execute(
                    select(UserWorldKnowledge).where(UserWorldKnowledge.user_id == user_id)
                )
                wk = wk_result.scalar_one_or_none()
                if not wk:
                    wk = UserWorldKnowledge(user_id=user_id)
                    session.add(wk)
                
                wk.hawkins_baseline = world_avg_hawkins
                wk.spheres_completed = completed_spheres
                wk.overall_pattern = "Комплексный паттерн развития."

            await session.commit()
            
            # Also rebuild portrait
            await build_portrait_for_sphere(session, user_id, sphere)
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Knowledge aggregation error: {e}")


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
    """Start or resume a synchronization session for a card."""
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

    # Check for existing incomplete session to resume
    existing_result = await db.execute(
        select(SyncSession).where(
            SyncSession.card_progress_id == request.card_progress_id,
            SyncSession.user_id == request.user_id,
            SyncSession.is_complete == False,
        ).order_by(SyncSession.id.desc())
    )
    existing_session = existing_result.scalars().first()

    if existing_session:
        # Resume: return current phase content without charging energy
        # Resume: return current phase content without charging energy
        current_phase = existing_session.current_phase
        transcript = list(existing_session.session_transcript or [])
        
        # Get last assistant message if possible
        phase_content = "Продолжаем с места, где остановились..."
        for msg in reversed(transcript):
            if msg.get("role") == "assistant":
                phase_content = msg.get("content")
                break
        
        return {
            "session_id": existing_session.id,
            "current_phase": current_phase,
            "is_complete": False,
            "phase_content": phase_content,
            "resumed": True,
        }

    # Get user
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()

    # Check energy for new session
    can_spend = await spend_energy(db, user, "sync")
    if not can_spend:
        raise HTTPException(status_code=402, detail="Недостаточно ✦ Энергии")

    # Create new sync session
    session = SyncSession(
        user_id=request.user_id,
        card_progress_id=request.card_progress_id,
        archetype_id=card.archetype_id,
        sphere=card.sphere,
        current_phase=0, # Intro
        phase_data={"current_layer": "intro", "sub_phase": 0},
        session_transcript=[]
    )
    db.add(session)

    # Update card status
    card.status = CardStatus.IN_SYNC
    db.add(card)

    await db.commit()
    await db.refresh(session)

    # 1. Generate Intro content
    ai_content = await run_avatar_layer(
        layer="intro",
        archetype_id=card.archetype_id,
        sphere=card.sphere,
        previous_messages=[],
    )

    # Store first AI message
    session.session_transcript = [{"role": "assistant", "content": ai_content}]
    db.add(session)
    await db.commit()

    return {
        "session_id": session.id,
        "current_phase": 0,
        "is_complete": False,
        "phase_content": ai_content,
        "resumed": False,
    }
@router.post("/phase")
async def process_phase(
    request: PhaseRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Fetch current session state
    result = await db.execute(
        select(SyncSession).where(
            SyncSession.id == request.sync_session_id,
            SyncSession.user_id == request.user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()

    # Fetch current session state
    # Filter transcript to ensure no None/null entries or non-dict items
    raw_transcript = session.session_transcript or []
    transcript = []
    for m in raw_transcript:
        if isinstance(m, dict) and m.get("role") and m.get("content") is not None:
            transcript.append({"role": m["role"], "content": str(m["content"])})
    
    state = dict(session.phase_data or {"current_layer": "intro", "sub_phase": 0})
    current_layer = state.get("current_layer", "intro")
    sub_phase = state.get("sub_phase", 0)

    # Add user response to transcript (skip if empty/None — e.g. intro "Enter" click)
    user_response_text = request.user_response or ""
    
    # Ensure valid history for intro transition: OpenAI requires alternating roles
    if current_layer == "intro" and not user_response_text:
        user_response_text = "[Войти]"

    if user_response_text:
        # Safety net: ensure transcript has the assistant's intro message
        if not transcript:
             transcript.append({"role": "assistant", "content": "..."})
        
        transcript.append({"role": "user", "content": str(user_response_text)})

    # 1. Determine next move
    if current_layer == "intro":
        # Always move to Layer 1 from Intro
        next_layer = "1"
        should_move_deeper = True
        is_abstract = False
    else:
        is_abstract = is_abstract_response(user_response_text)
        should_move_deeper = not is_abstract or sub_phase >= 2
    
    if should_move_deeper:
        # Move to next layer
        if current_layer == "intro":
            next_layer = "1"
            new_sub_phase = 0
            new_phase_val = 1
        elif current_layer == "1":
            next_layer = "2"
            new_sub_phase = 0
            new_phase_val = 2
        elif current_layer == "2":
            next_layer = "3"
            new_sub_phase = 0
            new_phase_val = 3
        elif current_layer == "3":
            next_layer = "4"
            new_sub_phase = 0
            new_phase_val = 4
        elif current_layer == "4":
            next_layer = "mirror"
            new_sub_phase = 0
            new_phase_val = 5
        else:
            next_layer = "mirror"
            new_sub_phase = 0
            new_phase_val = 5
    else:
        # Stay in same layer, narrow down
        next_layer = current_layer
        new_sub_phase = sub_phase + 1
        new_phase_val = session.current_phase 

    # 2. Handle Mirror Analysis (Final)
    if next_layer == "mirror":
        analysis = await run_mirror_analysis(
            session.archetype_id, session.sphere, transcript
        )
        
        # Save results (Level 3 Knowledge Cell)
        session.is_complete = True
        session.current_phase = 5
        session.session_transcript = transcript
        session.real_picture = analysis.get("real_picture")
        session.core_pattern = analysis.get("core_pattern")
        session.shadow_active = analysis.get("shadow_active")
        session.body_anchor = analysis.get("body_anchor")
        session.first_insight = analysis.get("first_insight")
        session.hawkins_score = analysis.get("hawkins_score", 100)
        session.hawkins_level = analysis.get("hawkins_level", "Страх")
        
        # Backward compatibility fields
        session.extracted_core_belief = session.core_pattern
        session.extracted_shadow_pattern = session.shadow_active
        session.extracted_body_anchor = session.body_anchor
        
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
            card.rank = hawkins_to_rank(card.hawkins_peak)
            card.sync_sessions_count += 1
            db.add(card)

        # Award XP
        if user:
            user.xp = (user.xp or 0) + session.hawkins_score
            while user.evolution_level < 100 and user.xp >= calculate_xp_for_level(user.evolution_level + 1):
                user.evolution_level += 1
            db.add(user)

        await db.commit()

        # 3. Trigger context aggregation in background
        background_tasks.add_task(_aggregate_knowledge, request.user_id, session.sphere)

        return {
            "session_id": session.id,
            "current_phase": 5,
            "is_complete": True,
            "phase_content": f"Синхронизация завершена. Проявленный паттерн: {session.core_pattern}",
            "insights": analysis,
        }

    try:
        # 3. Handle next narrative step
        ai_content = await run_avatar_layer(
            layer=next_layer,
            archetype_id=session.archetype_id,
            sphere=session.sphere,
            previous_messages=transcript,
            is_narrowing=(not should_move_deeper)
        )

        # Update session state: Ensure context is saved
        transcript.append({"role": "assistant", "content": str(ai_content)})
        session.session_transcript = transcript
        session.phase_data = {"current_layer": next_layer, "sub_phase": new_sub_phase}
        session.current_phase = new_phase_val
        
        # Explicitly mark as modified for SQLAlchemy just in case
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "phase_data")
        flag_modified(session, "session_transcript")
        
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return {
            "session_id": session.id,
            "current_phase": session.current_phase,
            "is_complete": False,
            "phase_content": ai_content,
            "layer": next_layer,
            "sub_phase": new_sub_phase,
            "transcript_len": len(transcript)
        }
    except Exception as e:
        import logging
        import traceback
        logging.getLogger(__name__).error(f"Sync Phase Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Ошибка при генерации фазы синхронизации")
