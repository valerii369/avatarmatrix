from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional

from app.database import get_db, AsyncSessionLocal
from app.models import User, AssistantSession, CardProgress, CardStatus
from app.agents.assistant_agent import generate_assistant_response
from app.core.economy import spend_energy, award_xp
from app.core.astrology.vector_matcher import match_text_to_archetypes
from app.rro.ocean.hub import OceanService
from app.rro.session.river import SessionRiver

router = APIRouter()

class AssistantInitRequest(BaseModel):
    user_id: int

class AssistantChatRequest(BaseModel):
    user_id: int
    session_id: int
    message: str

@router.post("/init")
async def init_assistant(request: AssistantInitRequest, db: AsyncSession = Depends(get_db)):
    user_res = await db.execute(select(User).where(User.id == request.user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for active session
    active_session_res = await db.execute(
        select(AssistantSession).where(
            AssistantSession.user_id == request.user_id,
            AssistantSession.is_active == True
        )
    )
    session = active_session_res.scalar_one_or_none()
    
    is_first_touch = False
    if not session:
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(AssistantSession.id)).where(AssistantSession.user_id == request.user_id)
        )
        total_sessions_count = result.scalar() or 0
        is_first_touch = total_sessions_count == 0
        
        session = AssistantSession(
            user_id=request.user_id,
            metadata_json={"first_touch": is_first_touch}
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    return {
        "session_id": session.id,
        "is_first_touch": is_first_touch
    }

@router.post("/chat")
async def assistant_chat(request: AssistantChatRequest, db: AsyncSession = Depends(get_db)):
    session_res = await db.execute(
        select(AssistantSession).where(
            AssistantSession.id == request.session_id,
            AssistantSession.user_id == request.user_id,
            AssistantSession.is_active == True
        )
    )
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")

    user_res = await db.execute(select(User).where(User.id == request.user_id))
    user = user_res.scalar_one_or_none()

    # Detect return after pause (> 24h)
    from datetime import datetime, timedelta, timezone
    is_returning_after_pause = False
    
    # Check if this is a fresh start in an active session (no previous messages) 
    # and there was a previous session more than 24h ago
    if not session.messages_json:
        last_session_res = await db.execute(
            select(AssistantSession).where(
                AssistantSession.user_id == request.user_id,
                AssistantSession.id != session.id
            ).order_by(AssistantSession.created_at.desc()).limit(1)
        )
        last_session = last_session_res.scalar_one_or_none()
        if last_session and last_session.created_at:
            # Assumes created_at is UTC
            diff = datetime.now(timezone.utc) - last_session.created_at.replace(tzinfo=timezone.utc)
            if diff > timedelta(hours=24):
                is_returning_after_pause = True

    # Process message
    ai_response, sphere, increment, activated = await generate_assistant_response(
        db, request.user_id, session.messages_json, request.message, 
        gender=user.gender or "не указан",
        user_name=user.first_name or "Путешественник",
        is_returning_after_pause=is_returning_after_pause
    )

    # Update session
    session.messages_json.append({"role": "user", "content": request.message})
    session.messages_json.append({"role": "assistant", "content": ai_response})
    
    # Update resonance
    scores = session.resonance_scores.copy() if session.resonance_scores else {}
    current_score = scores.get(sphere, 0.0)
    new_score = min(2.0, current_score + increment)
    scores[sphere] = new_score
    session.resonance_scores = scores
    
    # Logic for discovering cards (like in reflection but via resonance score)
    discovered_cards = []
    if new_score >= 1.0:
        # Use vector search to find specific cards for this sphere that match the dialogue
        matches = await match_text_to_archetypes(db, request.message, top_k=3)
        for arch_id_match, sphere_match, score_match in matches:
            if sphere_match == sphere:
                cp_stmt = select(CardProgress).where(
                    CardProgress.user_id == request.user_id,
                    CardProgress.archetype_id == arch_id_match,
                    CardProgress.sphere == sphere_match
                )
                cp_res = await db.execute(cp_stmt)
                cp = cp_res.scalar_one_or_none()
                if not cp:
                    cp = CardProgress(user_id=request.user_id, archetype_id=arch_id_match, sphere=sphere_match, status=CardStatus.LOCKED)
                    db.add(cp)
                
                if cp.status == CardStatus.LOCKED:
                    cp.status = CardStatus.RECOMMENDED
                    cp.is_recommended_ai = True
                    discovered_cards.append({"archetype_id": arch_id_match, "sphere": sphere_match})
                    # Reset resonance after discovery to allow next cycle
                    scores[sphere] = 0.0
                    session.resonance_scores = scores
                    break

    db.add(session)
    await db.commit()

    return {
        "ai_response": ai_response,
        "resonance": {
            "sphere": sphere,
            "score": new_score,
            "increment": increment
        },
        "discovered_cards": discovered_cards
    }

@router.post("/finish")
async def finish_assistant(
    request: AssistantChatRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    session_res = await db.execute(
        select(AssistantSession).where(
            AssistantSession.id == request.session_id,
            AssistantSession.user_id == request.user_id,
            AssistantSession.is_active == True
        )
    )
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")

    # Generate summary of the dialogue
    from app.agents.assistant_agent import generate_diary_summary, extract_and_save_insights
    summary = await generate_diary_summary(db, session.messages_json)
    
    # Extract semantic memory (atomic insights)
    await extract_and_save_insights(db, request.user_id, session.messages_json, session.id)
    
    session.is_active = False
    session.final_analysis = {"diary_summary": summary}
    db.add(session)
    await db.commit()
    
    # Level 2 & 3 Pipeline: Update the Hub (Ocean - User Print)
    from app.rro.session.river import SessionRiver
    from app.rro.ocean.hub import OceanService
    async def _run_session_rro_pipeline(u_id, s_id):
        async with AsyncSessionLocal() as session_db:
            try:
                # Get fresh data
                res = await session_db.execute(select(AssistantSession).where(AssistantSession.id == s_id))
                as_session = res.scalar_one_or_none()
                if not as_session: return
                
                # Level 2: River
                river = SessionRiver()
                interpretation = await river.flow(session_db, u_id, {"history": as_session.messages_json})
                
                if interpretation:
                    # Level 3: Ocean
                    await OceanService.update_ocean(session_db, u_id, [interpretation])
                    await session_db.commit()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Session RRO Pipeline Error: {e}")

    background_tasks.add_task(_run_session_rro_pipeline, request.user_id, session.id)
    
    return {
        "status": "session_closed",
        "diary_summary": summary
    }

@router.post("/save-to-diary")
async def save_to_diary(request: AssistantChatRequest, db: AsyncSession = Depends(get_db)):
    session_res = await db.execute(
        select(AssistantSession).where(
            AssistantSession.id == request.session_id,
            AssistantSession.user_id == request.user_id
        )
    )
    session = session_res.scalar_one_or_none()
    if not session or not session.final_analysis:
        raise HTTPException(status_code=404, detail="Session or summary not found")

    summary = session.final_analysis.get("diary_summary", "Общение с цифровым помощником.")
    
    # Create Diary Entry
    from app.models import DiaryEntry
    entry = DiaryEntry(
        user_id=request.user_id,
        text=summary,
        source="ASSSISTANT",
        meta_data={"session_id": session.id}
    )
    db.add(entry)
    
    # Award XP for reflection
    await award_xp(db, request.user_id, 15, "assistant_reflection")
    
    await db.commit()
    return {"status": "saved"}
