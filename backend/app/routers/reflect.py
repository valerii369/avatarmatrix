from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from app.database import get_db
from app.models import User, DiaryEntry, CardProgress, ReflectionSession
from app.models.card_progress import CardStatus
from app.services.ocean.economy_service import spend_energy, award_xp
from app.agents.master_agent import analyze_reflection
from app.agents.river.reflect_agent import reflection_chat_message
from app.services.rain.astrology.vector_matcher import match_text_to_archetypes


router = APIRouter()


class ReflectRequest(BaseModel):
    user_id: int
    content: str
    is_voice: bool = False
    use_ai: bool = True

class ChatMessageRequest(BaseModel):
    user_id: int
    session_id: int
    message: str


@router.post("")
async def daily_reflection(request: ReflectRequest, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")



    # Determine action and cost
    action = "reflection_ai" if request.use_ai else "reflection_simple"
    can_spend = await spend_energy(db, user, action)
    if not can_spend:
        cost = 20 if request.use_ai else 5
        raise HTTPException(status_code=402, detail=f"Недостаточно ✦ Энергии ({cost}✦ для записи)")

    # Run AI Analysis for AI/Sphere classification
    analysis = await analyze_reflection(request.content, gender=user.gender or "не указан", language=user.language)
    h_score = analysis.get("hawkins_score", 200)
    ai_feedback = analysis.get("ai_analysis", "")
    sphere = analysis.get("sphere", "IDENTITY")
    arch_id = analysis.get("archetype_id", 0)
    
    discovered_cards = []
    
    if request.use_ai:
        energy_msg = "-20 ✦ за глубокую рефлексию"
        # AI Card Accumulation & Discovery
        matches = await match_text_to_archetypes(db, request.content, top_k=5)
        new_recommendations_count = 0
        
        for arch_id_match, sphere_match, score_match in matches:
            cp_stmt = select(CardProgress).where(
                CardProgress.user_id == request.user_id,
                CardProgress.archetype_id == arch_id_match,
                CardProgress.sphere == sphere_match
            )
            cp_res = await db.execute(cp_stmt)
            cp = cp_res.scalar_one_or_none()
            if not cp:
                cp = CardProgress(user_id=request.user_id, archetype_id=arch_id_match, sphere=sphere_match, status=CardStatus.LOCKED, ai_score=0.0)
                db.add(cp)
            
            increment = score_match * 0.3
            cp.ai_score = min(2.0, cp.ai_score + increment)
            
            if cp.ai_score >= 1.0 and cp.status == CardStatus.LOCKED and new_recommendations_count < 2:
                cp.status = CardStatus.RECOMMENDED
                cp.is_recommended_ai = True
                new_recommendations_count += 1
                discovered_cards.append({"archetype_id": arch_id_match, "sphere": sphere_match, "ai_score": cp.ai_score})
        
        await award_xp(db, user, 25) # Higher bonus for AI reflection
    else:
        # Simple diary entry with sphere classification
        energy_msg = "-5 ✦ за запись в дневник"
        await award_xp(db, user, 10)

    # Save to DiaryEntry
    entry = DiaryEntry(
        user_id=request.user_id,
        archetype_id=arch_id,
        sphere=sphere,
        content=request.content,
        entry_type="reflection",
        hawkins_score=h_score if request.use_ai else None,
        ai_analysis=ai_feedback if request.use_ai else None,
    )
    db.add(entry)
    await db.commit()

    return {
        "message": energy_msg,
        "energy_awarded": 0,
        "discovered_cards": discovered_cards,
        "analysis": {
            "hawkins_score": h_score if request.use_ai else None,
            "hawkins_level": analysis.get("hawkins_level", "") if request.use_ai else "Diary",
            "ai_analysis": ai_feedback,
            "sphere": sphere
        }
    }

@router.post("/chat/start")
async def start_reflection_chat(request: ReflectRequest, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Списание энергии (20 за сессию с ИИ)
    can_spend = await spend_energy(db, user, "reflection_ai")
    if not can_spend:
        raise HTTPException(status_code=402, detail="Недостаточно ✦ Энергии (20✦ для глубокой рефлексии)")

    # Первичный анализ для определения сферы
    analysis = await analyze_reflection(request.content, gender=user.gender or "не указан", language=user.language)
    sphere = analysis.get("sphere", "IDENTITY")
    
    # Создание сессии (с начальной фазой 1 - Entrance)
    session = ReflectionSession(
        user_id=request.user_id,
        sphere=sphere,
        current_phase=1,
        messages_json=[{"role": "user", "content": request.content}]
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Первый ответ ИИ
    ai_response, phase_complete, analysis_dict = await reflection_chat_message(
        chat_history=[],
        user_message=request.content,
        sphere=sphere,
        current_phase=session.current_phase,
        gender=user.gender or "не указан"
    )
    
    # Продвижение по фазам, если ИИ считает, что цель фазы достигнута
    if phase_complete:
        session.current_phase += 1
        
    session.messages_json.append({"role": "assistant", "content": ai_response})
    
    # Commit AI response
    db.add(session)
    await db.commit()

    return {
        "session_id": session.id,
        "sphere": sphere,
        "current_phase": session.current_phase,
        "ai_response": ai_response,
        "emotion": analysis_dict.get("extracted_emotion", ""),
        "ready": False # Start never triggers a full finish
    }

@router.post("/chat/message")
async def send_reflection_message(request: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    session_result = await db.execute(
        select(ReflectionSession).where(
            ReflectionSession.id == request.session_id, 
            ReflectionSession.user_id == request.user_id,
            ReflectionSession.is_active == True
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or inactive")

    # Добавляем сообщение пользователя
    session.messages_json.append({"role": "user", "content": request.message})
    
    # Предварительно сохраняем контекст для запроса (без нового сообщения юзера, мы передаем его отдельно)
    chat_history = session.messages_json[:-1]
    
    # Генерируем ответ ИИ с учетом текущей фазы
    user_gender = "не указан"
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user_gender = user.gender or "не указан"

    ai_response, phase_complete, analysis_dict = await reflection_chat_message(
        chat_history=chat_history,
        user_message=request.message,
        sphere=session.sphere,
        current_phase=session.current_phase,
        gender=user_gender
    )
    
    # Progress the state machine
    if phase_complete:
        session.current_phase += 1
        
    # Check if we moved past the final Phase 4
    is_ready = session.current_phase > 4
        
    session.messages_json.append({"role": "assistant", "content": ai_response})
    
    # Store interim analysis results (emotion/hawkins) safely for the finish endpoint
    new_analysis = session.final_analysis.copy() if session.final_analysis else {}
    new_analysis["last_emotion"] = analysis_dict.get("extracted_emotion", "")
    
    # Если мы прошли 4ю фазу (Интеграция), там сгенерировался шкала Хокинса! Сохраняем.
    if analysis_dict.get("hawkins_score", 0) > 0:
        new_analysis["hawkins_score"] = analysis_dict["hawkins_score"]
        
    session.final_analysis = new_analysis
    
    db.add(session)
    await db.commit()

    return {
        "ai_response": ai_response, 
        "current_phase": min(session.current_phase, 4), # Cap at 4 for UI
        "emotion": analysis_dict.get("extracted_emotion", ""),
        "ready": is_ready
    }

@router.post("/chat/finish")
async def finish_reflection_chat(request: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    session_result = await db.execute(
        select(ReflectionSession).where(
            ReflectionSession.id == request.session_id, 
            ReflectionSession.user_id == request.user_id,
            ReflectionSession.is_active == True
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Итоговый анализ всего диалога
    full_transcript = "\n".join([f"{m['role']}: {m['content']}" for m in session.messages_json])
    user_gender = "не указан"
    user_lang = "ru"
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user_gender = user.gender or "не указан"
        user_lang = user.language

    analysis = await analyze_reflection(full_transcript, gender=user_gender, language=user_lang)
    
    # Обогащаем финальный анализ тем Хокинсом, который мы вытащили на 4-й фазе прямо в агенте (если он там есть)
    agent_hawkins = session.final_analysis.get("hawkins_score") if session.final_analysis else None
    if agent_hawkins and agent_hawkins > 0:
        analysis["hawkins_score"] = agent_hawkins
        
    # Закрываем сессию
    session.is_active = False
    session.final_analysis = analysis
    
    # Сохраняем в дневник как результат рефлексии
    entry = DiaryEntry(
        user_id=request.user_id,
        sphere=session.sphere,
        content=session.messages_json[0]["content"], # С чего всё началось
        entry_type="reflection",
        hawkins_score=analysis.get("hawkins_score", 200),
        ai_analysis=analysis.get("ai_analysis", ""),
    )
    db.add(entry)
    
    # Начисляем опыт (25 за глубокую сессию)
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        await award_xp(db, user, 25)

    # Векторное сопоставление (карты)
    matches = await match_text_to_archetypes(db, full_transcript, top_k=5)
    discovered_cards = []
    for arch_id_match, sphere_match, score_match in matches:
        cp_stmt = select(CardProgress).where(
            CardProgress.user_id == request.user_id,
            CardProgress.archetype_id == arch_id_match,
            CardProgress.sphere == sphere_match
        )
        cp_res = await db.execute(cp_stmt)
        cp = cp_res.scalar_one_or_none()
        if not cp:
            cp = CardProgress(user_id=request.user_id, archetype_id=arch_id_match, sphere=sphere_match, status=CardStatus.LOCKED, ai_score=0.0)
            db.add(cp)
        
        increment = score_match * 0.4 # Чуть больше за глубокую сессию
        cp.ai_score = min(2.0, cp.ai_score + increment)
        
        if cp.ai_score >= 1.0 and cp.status == CardStatus.LOCKED:
            cp.status = CardStatus.RECOMMENDED
            cp.is_recommended_ai = True
            discovered_cards.append({"archetype_id": arch_id_match, "sphere": sphere_match})

    await db.commit()

    return {
        "message": "Сессия завершена",
        "discovered_cards": discovered_cards,
        "analysis": analysis
    }
