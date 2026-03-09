"""
Sync router: manage 10-phase synchronization sessions.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import CardProgress, SyncSession, User, SphereKnowledge, UserWorldKnowledge, UserPortrait
from app.models.card_progress import CardStatus
from app.agents.sync_agent import run_avatar_layer, get_response_metrics
from app.agents.analytic_agent import run_mirror_analysis, extract_response_features, update_user_portrait
from app.core.feature_extractor import FeatureExtractor
from app.core.economy import spend_energy, hawkins_to_rank, award_xp, process_card_rank_up, XP_VALUES
from app.core.portrait_builder import build_portrait_for_sphere
from app.database import AsyncSessionLocal

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

async def _get_portrait_context(db: AsyncSession, user_id: int, sphere: str) -> dict:
    """Retrieves previous patterns and symbols for the AI prompt."""
    res = await db.execute(
        select(UserPortrait).where(UserPortrait.user_id == user_id, UserPortrait.sphere == sphere)
    )
    portrait = res.scalar_one_or_none()
    if not portrait or not portrait.cards_data:
        return {}
    
    # Collect unique symbols and patterns from all cards in this sphere
    symbols = []
    patterns = []
    anchors = []
    
    for card in portrait.cards_data:
        if card.get("recurring_symbol"): symbols.append(card["recurring_symbol"])
        if card.get("core_pattern"): patterns.append(card["core_pattern"])
        if card.get("body_anchor"): anchors.append(card["body_anchor"])
    
    return {
        "symbols": ", ".join(list(set(symbols))[:5]),
        "patterns": ", ".join(list(set(patterns))[:5]),
        "body_anchors": ", ".join(list(set(anchors))[:5])
    }


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

    # Get context from portrait
    portrait_ctx = await _get_portrait_context(db, request.user_id, card.sphere)

    # 1. Generate Intro content
    ai_content = await run_avatar_layer(
        db=db,
        session_id=session.id,
        layer="intro",
        archetype_id=card.archetype_id,
        sphere=card.sphere,
        previous_messages=[],
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
        metrics = get_response_metrics(user_response_text)
        # Store metrics in session state per phase
        if "metrics" not in state:
            state["metrics"] = {}
        state["metrics"][current_layer] = metrics
        
        # Heuristic for abstraction: too short or no body/objects
        is_abstract = metrics["length"] < 10 or (not metrics["has_body"] and not metrics["has_objects"])
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

    # 2. Handle Mirror Analysis (Final)
    if next_layer == "mirror":
        # Get context from portrait for continuity in analysis
        portrait_ctx = await _get_portrait_context(db, request.user_id, session.sphere)
        
        analysis = await run_mirror_analysis(
            session.archetype_id, session.sphere, transcript, session.phase_data, portrait_context=portrait_ctx
        )
        
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
        
        # Save mental cells
        session.mental_thinking = analysis.get("mental_thinking")
        session.mental_reactions = analysis.get("mental_reactions")
        session.mental_patterns = analysis.get("mental_patterns")
        session.mental_aspirations = analysis.get("mental_aspirations")
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
        background_tasks.add_task(_aggregate_knowledge, request.user_id, session.sphere)
        background_tasks.add_task(FeatureExtractor.process_sync_session, db, session.id, request.user_id)
        background_tasks.add_task(update_user_portrait, db, request.user_id, session.id)

        return {
            "session_id": session.id,
            "current_phase": 6,
            "is_complete": True,
            "phase_content": f"Синхронизация завершена. Проявленный паттерн: {session.core_pattern}",
            "insights": analysis,
        }

    try:
        # Get context from portrait for continuity
        portrait_ctx = await _get_portrait_context(db, request.user_id, session.sphere)

        # 3. Handle next narrative step
        ai_content = await run_avatar_layer(
            db=db,
            session_id=session.id,
            layer=next_layer,
            archetype_id=session.archetype_id,
            sphere=session.sphere,
            previous_messages=transcript,
            is_narrowing=(not should_move_deeper),
            portrait_context=portrait_ctx
        )

        # 4. Log interaction (Self-Learning Layer 1)
        if current_layer != "intro" and user_response_text:
            try:
                # Find the scene that was shown for the phase we just COMPLETED
                # (current_layer is the layer the user just responded to)
                set_res = await db.execute(select(SceneSet).where(SceneSet.session_id == session.id))
                scene_set = set_res.scalar_one_or_none()
                if scene_set:
                    layer_int = int(current_layer)
                    item_res = await db.execute(
                        select(SceneSetItem).where(
                            SceneSetItem.scene_set_id == scene_set.id,
                            SceneSetItem.position == layer_int
                        )
                    )
                    item = item_res.scalar_one_or_none()
                    if item:
                        # Calculate timing
                        # We need the timestamp when the AI message was sent
                        # state["timing"][f"{current_layer}_{sub_phase}"]
                        ai_ts_str = state.get("timing", {}).get(f"{current_layer}_{sub_phase}")
                        reading_time = 0
                        if ai_ts_str:
                            ai_ts = datetime.datetime.fromisoformat(ai_ts_str)
                            user_ts = datetime.datetime.fromisoformat(user_timestamp)
                            reading_time = (user_ts - ai_ts).total_seconds()

                        from app.agents.sync_agent import get_embedding
                        resp_emb = await get_embedding(user_response_text)

                        # NEW: Extract structured features for research and future training
                        extracted_feats = await extract_response_features(
                            scene_text=item.scene.scene_text if hasattr(item, 'scene') else "",
                            user_response=user_response_text,
                            archetype_id=session.archetype_id,
                            sphere=session.sphere
                        )

                        interaction = SceneInteraction(
                            user_id=request.user_id,
                            session_id=session.id,
                            scene_id=item.scene_id,
                            layer_index=layer_int,
                            reading_time=reading_time,
                            response_text=user_response_text,
                            response_embedding=resp_emb,
                            response_length=len(user_response_text),
                            extracted_features=extracted_feats
                        )
                        db.add(interaction)
            except Exception as ex:
                import logging
                logging.getLogger(__name__).error(f"SceneInteraction logging failed: {ex}")

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
