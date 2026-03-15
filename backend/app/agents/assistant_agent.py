"""
Assistant Agent (The Mirror):
1. Aggregates all user knowledge (Ocean, Astro, Sessions, Diary).
2. Acts as a digital reflection of the user.
3. Tracks 'Resonance' score to unlock/activate cards during dialogue.
"""
import json
import logging
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from app.config import settings
from app.agents.common import client
from app.models import User, SyncSession, SphereKnowledge, AssistantSession, UserMemory, CardProgress, CardStatus
from app.core.user_print_manager import OceanService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import NatalChart, SyncSession, AlignSession, DiaryEntry

logger = logging.getLogger(__name__)

class AssistantResponse(BaseModel):
    ai_response: str = Field(description="Текст ответа. Глубокий, эмпатичный, отражающий суть пользователя.")
    resonance_sphere: str = Field(default="IDENTITY", description="Сфера, которая наиболее резонирует с текущим сообщением пользователя.")
    resonance_score_increment: float = Field(default=0.0, description="На сколько увеличить балл резонанса для этой сферы (0.0 - 0.5).")
    activated_card: bool = Field(default=False, description="Установи в True, если резонанс достиг пика и пора 'проявить' карту.")

async def get_comprehensive_context(db: AsyncSession, user_id: int) -> str:
    """Collects all available data about the user into a text context."""
    # 1. User Print (The Ocean) - Primary source
    ocean = await OceanService.get_ocean(db, user_id)
    ocean_text = ocean.model_dump_json() if ocean else "Данные Океана (Паспорта Личности) отсутствуют."

    # 2. Exposed Archetypes (CardProgress)
    # Fetch cards that are ALIGNED or SYNCED (Exposed/Activated)
    stmt = select(CardProgress).where(
        CardProgress.user_id == user_id,
        CardProgress.status.in_([CardStatus.ALIGNED, CardStatus.SYNCED])
    )
    result = await db.execute(stmt)
    exposed_cards = result.scalars().all()
    
    cards_context = "ПРОЯВЛЕННЫЕ АРХЕТИПЫ (ВАШИ ИНСТРУМЕНТЫ):\n"
    if exposed_cards:
        for card in exposed_cards:
            # Grouping by sphere for clarity
            cards_context += f"- Сфера '{card.sphere}': Архитип ID {card.archetype_id} (Статус: {card.status})\n"
    else:
        cards_context += "Нет проявленных архетипов. Пользователь находится в процессе первичной сонастройки.\n"

    context = f"""
ДАННЫЕ ПОЛЬЗОВАТЕЛЯ (ОКЕАН/ПАСПОРТ):
{ocean_text}

{cards_context}
"""
    return context

async def search_user_memory(db: AsyncSession, user_id: int, query: str, limit: int = 5) -> str:
    """Searches long-term user memory for relevant insights."""
    try:
        from app.core.astrology.vector_matcher import _get_embedding
        query_embedding = await _get_embedding(query)
        
        stmt = select(UserMemory).where(
            UserMemory.user_id == user_id
        ).order_by(
            UserMemory.embedding.cosine_distance(query_embedding)
        ).limit(limit)
        
        result = await db.execute(stmt)
        memories = result.scalars().all()
        
        if not memories:
            return ""
            
        context = "\nВАШИ ПРОШЛЫЕ ИНСАЙТЫ:\n"
        for m in memories:
            context += f"- {m.content}\n"
        return context
    except Exception as e:
        logger.error(f"Memory Search Error: {e}")
        return ""

async def extract_and_save_insights(db: AsyncSession, user_id: int, chat_history: List[Dict[str, str]], session_id: int):
    """Analyzes dialogue to extract and save 'atomic insights' into UserMemory."""
    if len(chat_history) < 2: return
    
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])
    prompt = f"""Проанализируй диалог и выдели 1-3 ключевых факта или инсайта о пользователе, которые важно помнить.
Пиши каждый инсайт с новой строки, кратко, в утвердительной форме от третьего лица (например: 'Пользователь чувствует тревогу из-за новой работы').
Если ничего важного нет, напиши 'НЕТ'.

ДИАЛОГ:
{history_text}
"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        insights_text = response.choices[0].message.content.strip()
        if "НЕТ" in insights_text: return
        
        from app.core.astrology.vector_matcher import _get_embedding
        for line in insights_text.split("\n"):
            line = line.strip()
            if not line: continue
            
            emb = await _get_embedding(line)
            memory = UserMemory(
                user_id=user_id,
                content=line,
                embedding=emb,
                source="assistant",
                metadata_json={"session_id": session_id}
            )
            db.add(memory)
        await db.commit()
    except Exception as e:
        logger.error(f"Insight Extraction Error: {e}")

async def generate_assistant_response(
    db: AsyncSession, 
    user_id: int, 
    chat_history: List[Dict[str, str]], 
    user_message: str,
    gender: str = "не указан",
    user_name: str = "Путешественник",
    is_returning_after_pause: bool = False
) -> Tuple[str, str, float, bool]:
    """
    Super-Intelligent Assistant Logic with dynamic RAG.
    """
    context = await get_comprehensive_context(db, user_id)
    
    # Dynamic RAG: Determine if memory search is needed
    memory_context = ""
    if user_message:
        # Simple heuristic or LLM check can be added here. 
        # For 'super-intelligent' feel, we search if message has complexity.
        if len(user_message.split()) > 3:
            memory_context = await search_user_memory(db, user_id, user_message)

    system_prompt = f"""ТВОЕ ИМЯ: AVATAR.
Ты — СВЕРХУМНЫЙ ЦИФРОВОЙ ПОМОЩНИК и эрудированный ментор системы AVATAR.
Твоя сущность — квинтэссенция мудрости, технологий и глубокого понимания человеческой природы.

КТО ТЫ И ЧЕМ ПОЛЕЗЕН:
1. Высший Проводник: Ты связываешь внешние события жизни пользователя с его внутренним «Океаном» (Паспортом Личности).
2. Мастер Архетипов: Ты помогаешь «проявлять» (активировать) заблокированные сферы жизни, анализируя диалог и находя резонанс.
3. Решатель Жизненных Вопросов: Ты помогаешь разобраться в любых вопросах — от отношений и карьеры до глубоких экзистенциальных поисков, используя базу знаний AVATAR и данные натальной карты.

ПРАВИЛА ОБЩЕНИЯ (КРИТИЧЕСКИ):
1. Обращение только на «Вы» и по имени: {user_name}. НИКАКИХ «Высшее Я», «Пользователь» и прочих абстракций.
2. ЛОГИКА ПРИВЕТСТВИЯ:
   - Если история сообщений пуста: Кратко представься как AVATAR (проводник по 12 сферам и архетипам Океана). Предложи помощь в решении конкретных жизненных вопросов. Будь лаконичен.
   - Если is_returning_after_pause = True: Напиши «С возвращением, {user_name}».
   - Во всех остальных случаях: СРАЗУ к сути. ЗАПРЕЩЕНО использовать приветствия.
3. ТВОЕ ИМЯ: AVATAR.
4. СТИЛЬ: МАКСИМАЛЬНО СЖАТЫЙ И ЛАКОНИЧНЫЙ. 
   - Не пиши более 2-3 предложений, если запрос не требует глубокого анализа или подробного объяснения.
   - Избегай пустых любезностей и вводных слов. 
   - Умная краткость — твой приоритет.
5. Ты — Зеркало. Показывай суть, а не лей воду.
6. НИКОГДА НЕ ИСПОЛЬЗУЙ ФРАЗУ «Чем я могу Вам помочь?» или «О чем Вы хотите поговорить?». Задавай вектор сам или отвечай на запрос.

ОСНОВНОЙ КОНТЕКСТ (Паспорт Личности):
{context}

ФРАГМЕНТЫ ПАМЯТИ:
{memory_context}

ГЕНДЕР ПОЛЬЗОВАТЕЛЯ: {gender}
ЯЗЫК: RU
"""

    messages = [{"role": "system", "content": system_prompt}] + chat_history
    if user_message:
        messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": "Приветствуй меня кратко и по сути моей жизни."})

    try:
        # Force a thought process or just high-quality response
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            response_format={
                "type": "json_schema", 
                "json_schema": {"name": "assistant_schema", "schema": AssistantResponse.model_json_schema()}
            }
        )
        result_data = AssistantResponse.model_validate_json(response.choices[0].message.content)
        
        # Post-processing: remove repeated greetings if LLM ignored instructions
        clean_response = result_data.ai_response
        greetings = ["Здравствуйте", "Приветствую", "Привет", "Добрый день", "Добрый вечер"]
        if len(chat_history) > 0:
            for g in greetings:
                if clean_response.startswith(g):
                    # Remove the first sentence or just the greeting
                    import re
                    clean_response = re.sub(rf"^{g}.*?[.!?]\s*", "", clean_response)
                    break
        
        return (
            clean_response if clean_response.strip() else result_data.ai_response, 
            result_data.resonance_sphere, 
            result_data.resonance_score_increment,
            result_data.activated_card
        )
    except Exception as e:
        logger.error(f"Assistant Agent Error: {e}")
        # Return a neutral, professional response if LLM fails
        return ("Я — AVATAR. Я настраиваю глубокую связь с Вашим внутренним миром. Повторите, пожалуйста, Ваш запрос.", "IDENTITY", 0.0, False)

async def generate_diary_summary(db: AsyncSession, chat_history: List[Dict[str, str]]) -> str:
    """Generates a concise summary for the Diary."""
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])
    prompt = f"Напиши краткое резюме этого диалога для личного дневника пользователя (от 1-го лица, например 'Обсудили ...'). Максимум 2 предложение.\n\nДИАЛОГ:\n{history_text}"
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except:
        return "Проведен диалог с Цифровым Помощником."
