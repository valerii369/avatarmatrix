from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, CardProgress, AIDiagnosticSession
from app.models.card_progress import CardStatus
from app.agents.onboarding_agent import generate_onboarding_response, extract_onboarding_cards
from app.core.economy import process_referral_reward
from app.agents.common import SPHERES

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str
    
class OnboardingChatRequest(BaseModel):
    user_id: int
    chat_history: list[ChatMessage]
    
class OnboardingCalculateRequest(BaseModel):
    user_id: int
    chat_history: list[ChatMessage]

@router.post("/chat")
async def onboarding_chat(request: OnboardingChatRequest):
    """
    Generate the next message for the AI Diagnostic flow.
    We pass the entire chat history so it's stateless on the backend.
    """
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    gender = user.gender if user else None
    
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.chat_history]
    
    response_text, is_ready = await generate_onboarding_response(history_dicts, gender=gender)
    
    return {"text": response_text, "ready": is_ready}

@router.post("/calculate")
async def calculate_cards(request: OnboardingCalculateRequest, db: AsyncSession = Depends(get_db)):
    """
    Final step of AI Onboarding. 
    1. Extracts cards via LLM
    2. Updates CardProgress based on recommendations
    3. Sets user.onboarding_done = True
    """
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.chat_history]
    ai_recommendations = await extract_onboarding_cards(history_dicts)
    
    # Save the diagnostic session (use a separate DB session so failure is isolated)
    try:
        from app.database import AsyncSessionLocal as LocalSession
        async with LocalSession() as session_log:
            ai_session = AIDiagnosticSession(
                user_id=user.id,
                chat_history_json=history_dicts,
                ai_recommendations_json=ai_recommendations
            )
            session_log.add(ai_session)
            await session_log.commit()
    except Exception as e:
        import logging
        logging.warning(f"AI diagnostic session save failed (non-fatal): {e}")

    # Build a lookup for recommendations
    rec_lookup = {}
    for rec in ai_recommendations:
        arch_id = rec.get("archetype_id")
        sphere = rec.get("sphere", "").upper()
        score = rec.get("score", 0.7)
        if arch_id is not None and sphere:
            rec_lookup[(arch_id, sphere)] = score

    if not rec_lookup:
        # Fallback: mark onboarding done even if no specific cards found
        user.onboarding_done = True
        db.add(user)
        await db.commit()
        return {"success": True, "cards_found": 0, "message": "No card matches found"}

    # Fetch existing cards
    existing_result = await db.execute(select(CardProgress).where(CardProgress.user_id == user.id))
    existing_cards = {(cp.archetype_id, cp.sphere): cp for cp in existing_result.scalars().all()}

    sphere_keys = list(SPHERES.keys())
    ARCHETYPE_IDS = list(range(22))

    for arch_id in ARCHETYPE_IDS:
        for sphere_key in sphere_keys:
            key = (arch_id, sphere_key)
            score = rec_lookup.get(key)
            is_rec = score is not None
            
            if key in existing_cards:
                cp = existing_cards[key]
                if is_rec and not cp.is_recommended_ai:
                    cp.is_recommended_ai = True
                    cp.ai_score = score
                    if cp.status == CardStatus.LOCKED:
                        cp.status = CardStatus.RECOMMENDED
                    db.add(cp)
            else:
                status = CardStatus.RECOMMENDED if is_rec else CardStatus.LOCKED
                cp = CardProgress(
                    user_id=user.id,
                    archetype_id=arch_id,
                    sphere=sphere_key,
                    status=status,
                    is_recommended_ai=is_rec,
                    ai_score=score if is_rec else None
                )
                db.add(cp)
                
    # Mark onboarding as done
    user.onboarding_done = True
    db.add(user)
    
    # Process referral rewards
    await process_referral_reward(db, user)
    
    await db.commit()
    return {"success": True, "cards_found": len(ai_recommendations)}
