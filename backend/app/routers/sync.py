"""
Sync router: manage 5-phase synchronization sessions.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models import CardProgress, SyncSession, User
from app.models.card_progress import CardStatus
from app.agents.sync_agent import run_avatar_layer, get_response_metrics, autonomous_somatic_check
from app.agents.analytic_agent import run_mirror_analysis, extract_response_features
from app.services.evolution_service import EvolutionService
from app.rro.passport_service import PassportService

router = APIRouter()


async def _background_sync_processing(user_id: int, session_id: int, sphere: str) -> None:
    """Wrapper for background tasks to use a fresh session."""
    async with AsyncSessionLocal() as session:
        try:
            # 1. Level 2 & 3 Pipeline: Update the Hub (Ocean - User Print)
            from app.rro.sync.river import SyncRiver
            from app.rro.ocean.hub import OceanService
            
            sync_session_res = await session.execute(select(SyncSession).where(SyncSession.id == session_id))
            sync_session = sync_session_res.scalar_one_or_none()
            
            if sync_session:
                # Prepare Level 1 (Rain) data for the River
                rain_data = {
                    "session_id": session_id,
                    "transcript": sync_session.session_transcript,
                    "phase_data": sync_session.phase_data,
                    "archetype_id": sync_session.archetype_id,
                    "sphere": sync_session.sphere
                }
                
                # Level 2: River (Populates Passport)
                river = SyncRiver()
                await river.flow(session, user_id, rain_data)
                
                # Level 3: Ocean (Simplification)
                await OceanService.update_ocean(session, user_id)
                
                # User Evolution: Record session processing completion
                await EvolutionService.record_touch(
                    db=session,
                    user_id=user_id,
                    touch_type="SYNC_PROCESSED",
                    payload={"session_id": session_id, "sphere": sphere}
                )
            
            await session.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Background Sync Processing Failed: {e}")
            await session.rollback()


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

    # User Evolution: Record session start attempt
    await EvolutionService.record_touch(
        db=db,
        user_id=request.user_id,
        touch_type="SYNC_START_REQUEST",
        payload={"card_id": request.card_progress_id, "sphere": card.sphere}
    )
    
    # In RRO v3, scenes are generated dynamically by the LLM
    scenes_data = {}

    # Create new sync session
    session = SyncSession(
        user_id=request.user_id,
        card_progress_id=request.card_progress_id,
        archetype_id=card.archetype_id,
        sphere=card.sphere,
        current_phase=0, # Intro
        phase_data={
            "current_layer": "intro", 
            "sub_phase": 0, 
            "scenes": scenes_data,
            "timing": {
                "intro_0": datetime.datetime.utcnow().isoformat()
            }
        },
        session_transcript=[]
    )
    db.add(session)

    # Update card status
    card.status = CardStatus.IN_SYNC
    db.add(card)

    await db.commit()
    await db.refresh(session)

    # Get context from portrait
    # Get context from Passport instead of legacy Portrait
    passport_data = await PassportService.get_passport_json(db, request.user_id)
    astro_spheres = passport_data.get("astrology", {}).get("data", {}).get("spheres", {}) if passport_data else {}
    portrait_ctx = astro_spheres.get(card.sphere, {})

    # 1. Generate Intro content
    ai_content = await run_avatar_layer(
        layer="intro",
        archetype_id=card.archetype_id,
        sphere=card.sphere,
        previous_messages=[],
        scene_text=None,
        portrait_context=portrait_ctx
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
        
        import datetime
        user_timestamp = datetime.datetime.utcnow().isoformat()
        transcript.append({
            "role": "user", 
            "content": str(user_response_text),
            "created_at": user_timestamp
        })
        
        # Track timing in state for delay analysis
        if "timing" not in state:
            state["timing"] = {}
        state["timing"][f"{current_layer}_{sub_phase}_user"] = user_timestamp

    # 1. Determine next move
    if current_layer == "intro":
        # Always move to Layer 1 from Intro
        next_layer = "1"
        should_move_deeper = True
        is_abstract = False
        metrics = {"length": 0, "has_body": False, "has_objects": False}
    else:
        # NEW: Autonomous Somatic Check
        scene_text = state.get("scenes", {}).get(current_layer, {}).get("text", "")
        somatic_result = await autonomous_somatic_check(user_response_text, scene_text)
        
        is_abstract = not somatic_result.get("is_somatic", False)
        metrics = {
            "length": len(user_response_text),
            "has_body": somatic_result.get("has_body", False),
            "has_objects": somatic_result.get("has_objects", False),
            "ai_reason": somatic_result.get("reason")
        }
        
        # Store metrics in session state per phase
        if "metrics" not in state:
            state["metrics"] = {}
        state["metrics"][current_layer] = metrics
        
        should_move_deeper = not is_abstract or sub_phase >= 1 # Max 1 retry for abstract responses
    
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
            next_layer = "5"
            new_sub_phase = 0
            new_phase_val = 5
        elif current_layer == "5":
            next_layer = "mirror"
            new_sub_phase = 0
            new_phase_val = 6
        else:
            next_layer = "mirror"
            new_sub_phase = 0
            new_phase_val = 6
    else:
        # Stay in same layer, narrow down
        next_layer = current_layer
        new_sub_phase = sub_phase + 1
        new_phase_val = session.current_phase 

    # FAST-FAIL: Skip LLM completely if the user response is too abstract
    is_fast_fail = False
    ai_content = ""
    if not should_move_deeper and current_layer != "intro" and next_layer != "mirror":
        is_fast_fail = True
        ai_content = "Я слышу твои мысли. Но вернись в пространство. Что прямо сейчас происходит с твоим телом в ответ на это? Опиши ощущения или детали вокруг."

    # 2. Handle Mirror Analysis (Final)
    if next_layer == "mirror":
        # Get context from portrait for continuity in analysis
        passport_data = await PassportService.get_passport_json(db, request.user_id)
        astro_spheres = passport_data.get("astrology", {}).get("data", {}).get("spheres", {}) if passport_data else {}
        portrait_ctx = astro_spheres.get(session.sphere, {})
        
        analysis = await run_mirror_analysis(
            session.archetype_id, session.sphere, transcript, session.phase_data, portrait_context=portrait_ctx, db=db
        )
        
        # NEW: Save personal symbols if any were identified
        identified_syms = analysis.get("symbols_identified")
        if identified_syms:
            from app.core.symbolic_service import SymbolicService
            await SymbolicService.update_personal_symbols(db, request.user_id, identified_syms, session.sphere)
        
        # Save results (Level 3 Knowledge Cell)
        session.is_complete = True
        session.current_phase = 6
        session.session_transcript = transcript
        session.real_picture = analysis.get("real_picture")
        session.core_pattern = analysis.get("core_pattern")
        session.shadow_active = analysis.get("shadow_active")
        session.body_anchor = analysis.get("body_anchor")
        session.first_insight = analysis.get("first_insight")
        session.hawkins_score = analysis.get("hawkins_score", 100)
        session.hawkins_level = analysis.get("hawkins_level", "Страх")
        
        # Helper to join lists/strings
        def _to_str(val):
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val) if val is not None else None

        # Save mental cells
        session.mental_thinking = _to_str(analysis.get("mental_thinking"))
        session.mental_reactions = _to_str(analysis.get("mental_reactions"))
        session.mental_patterns = _to_str(analysis.get("mental_patterns"))
        session.mental_aspirations = _to_str(analysis.get("mental_aspirations"))
        session.recurring_symbol = analysis.get("recurring_symbol")
        
        # Save NEW diagnostic fields
        session.body_signal = analysis.get("body_signal")
        session.reaction_pattern = analysis.get("reaction_pattern")
        
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
            old_rank = card.rank
            card.status = CardStatus.SYNCED
            card.hawkins_current = session.hawkins_score
            
            # Update Knowledge Cell on Card
            card.mental_data = {
                "thinking": session.mental_thinking,
                "reactions": session.mental_reactions,
                "patterns": session.mental_patterns,
                "aspirations": session.mental_aspirations
            }

            if session.hawkins_score > card.hawkins_peak:
                card.hawkins_peak = session.hawkins_score
            
            new_rank = hawkins_to_rank(card.hawkins_peak)
            card.rank = new_rank
            
            # XP Awarding
            if user:
                # 1. Opening bonus
                if card.sync_sessions_count == 0:
                    await award_xp(db, user, XP_VALUES["card_opened"])
                
                # 2. Rank up XP
                await process_card_rank_up(db, user, old_rank, new_rank, session.hawkins_score)
                
            card.sync_sessions_count += 1
            db.add(card)

        await db.commit()

        # 3. Trigger context aggregation and behavioral analysis in background
        background_tasks.add_task(_background_sync_processing, request.user_id, session.id, session.sphere)

        return {
            "session_id": session.id,
            "current_phase": 6,
            "is_complete": True,
            "phase_content": f"Синхронизация завершена. Проявленный паттерн: {session.core_pattern}",
            "insights": analysis,
        }

    try:
        # Get context from portrait for continuity
        passport_data = await PassportService.get_passport_json(db, request.user_id)
        astro_spheres = passport_data.get("astrology", {}).get("data", {}).get("spheres", {}) if passport_data else {}
        portrait_ctx = astro_spheres.get(session.sphere, {})

        # 3. Handle next narrative step
        if not is_fast_fail and next_layer != "mirror":
            scene_text = state.get("scenes", {}).get(next_layer, {}).get("text")
            ai_content = await run_avatar_layer(
                layer=next_layer,
                archetype_id=session.archetype_id,
                sphere=session.sphere,
                previous_messages=transcript,
                scene_text=scene_text,
                is_narrowing=(not should_move_deeper),
                portrait_context=portrait_ctx
            )

        # 4. Log interaction (User Evolution)
        if current_layer != "intro" and user_response_text:
            await EvolutionService.record_touch(
                db=db,
                user_id=request.user_id,
                touch_type="SYNC_STEP",
                payload={
                    "session_id": session.id,
                    "layer": current_layer,
                    "sub_phase": sub_phase,
                    "response_length": len(user_response_text)
                }
            )

        # Update session state: Ensure context is saved
        timestamp = datetime.datetime.utcnow().isoformat()
        transcript.append({
            "role": "assistant", 
            "content": str(ai_content),
            "created_at": timestamp
        })
        session.session_transcript = transcript
        
        # Track timing for sub-phases to analyze delays
        if "timing" not in state:
            state["timing"] = {}
        state["timing"][f"{next_layer}_{new_sub_phase}"] = timestamp
        
        state["current_layer"] = next_layer
        state["sub_phase"] = new_sub_phase
        session.phase_data = state
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
