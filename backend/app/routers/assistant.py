from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional

from app.database import get_db
from app.models import User, AssistantSession, CardProgress, CardStatus
from app.agents.assistant_agent import generate_assistant_response
from app.core.economy import spend_energy, award_xp
from app.core.astrology.vector_matcher import match_text_to_archetypes

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
        # Check if user ever had a session
        total_sessions = await db.execute(
            select(AssistantSession).where(AssistantSession.user_id == request.user_id)
        )
        is_first_touch = len(total_sessions.all()) == 0
        
        session = AssistantSession(
            user_id=request.user_id,
            metadata_json={"first_touch": is_first_touch}
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Initial AI greeting/trigger
    ai_response, sphere, increment, activated = await generate_assistant_response(
        db, request.user_id, session.messages_json, "", gender=user.gender or "не указан"
    )
    
    session.messages_json.append({"role": "assistant", "content": ai_response})
    db.add(session)
    await db.commit()

    return {
        "session_id": session.id,
        "ai_response": ai_response,
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

    # Process message
    ai_response, sphere, increment, activated = await generate_assistant_response(
        db, request.user_id, session.messages_json, request.message, gender=user.gender or "не указан"
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
async def finish_assistant(request: AssistantChatRequest, db: AsyncSession = Depends(get_db)):
    session_res = await db.execute(
        select(AssistantSession).where(
            AssistantSession.id == request.session_id,
            AssistantSession.user_id == request.user_id
        )
    )
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    db.add(session)
    await db.commit()
    return {"status": "session_closed"}
