"""
Assistant Agent (The Mirror):
1. Aggregates all user knowledge (Ocean, Astro, Sessions, Diary).
2. Acts as a digital reflection of the user.
3. Tracks 'Resonance' score to unlock/activate cards during dialogue.
"""
import json
import logging
import re
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from app.config import settings
from app.agents.common import client
from app.models import (
    User, SyncSession, SphereKnowledge, AssistantSession, 
    UserMemory, CardProgress, CardStatus, NatalChart, 
    UserPortrait
)
from app.rro.ocean.hub import OceanService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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

    # 2. Episodic Memory (Last 5 sessions)
    stmt_sessions = select(AssistantSession).where(
        AssistantSession.user_id == user_id,
        AssistantSession.is_active == False
    ).order_by(AssistantSession.created_at.desc()).limit(5)
    sessions_res = await db.execute(stmt_sessions)
    last_sessions = sessions_res.scalars().all()
    
    episodic_context = "\nИСТОРИЯ ПОСЛЕДНИХ ДИАЛОГОВ (Эпизодическая память):\n"
    if last_sessions:
        for s in last_sessions:
            summary = s.final_analysis.get("diary_summary") if s.final_analysis else None
            if summary:
                date_str = s.created_at.strftime("%Y-%m-%d") if s.created_at else "Недавно"
                episodic_context += f"- [{date_str}]: {summary}\n"
    else:
        episodic_context += "Нет истории прошлых сессий.\n"

    # 3. Exposed Archetypes (CardProgress)
    stmt_cards = select(CardProgress).where(
        CardProgress.user_id == user_id,
        CardProgress.status.in_([CardStatus.ALIGNED, CardStatus.SYNCED])
    )
    result = await db.execute(stmt_cards)
    exposed_cards = result.scalars().all()
    
    cards_context = "ПРОЯВЛЕННЫЕ АРХЕТИПЫ (ВАШИ ИНСТРУМЕНТЫ):\n"
    if exposed_cards:
        for card in exposed_cards:
            cards_context += f"- Сфера '{card.sphere}': Архитип ID {card.archetype_id} (Статус: {card.status})\n"
    else:
        cards_context += "Нет проявленных архетипов.\n"

    context = f"""
ДАННЫЕ ПОЛЬЗОВАТЕЛЯ (ОКЕАН/ПАСПОРТ):
{ocean_text}

{episodic_context}

{cards_context}
"""
    return context

async def autonomous_reasoning(user_message: str, context: str) -> Dict[str, Any]:
    """
    Preliminary analysis step (Thinking State) to detect emotional tone and spheres.
    """
    prompt = f"""ПРОАНАЛИЗИРУЙ СООБЩЕНИЕ И КОНТЕКСТ:
1. Выдели доминирующую эмоцию или «вайб» сообщения.
2. Определи основную и вторичную сферу (из 12), о которых идет речь.
3. Коротко выдели одну скрытую связь между сферами (если есть).

СООБЩЕНИЕ: {user_message}
КОНТЕКСТ: {context[:1000]}...

ОТВЕТЬ В JSON:
{{
  "vibe": "string",
  "primary_sphere": "string",
  "secondary_sphere": "string",
  "cross_sphere_insight": "string"
}}
"""
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Reasoning Error: {e}")
        return {"vibe": "neutral", "primary_sphere": "IDENTITY", "secondary_sphere": None, "cross_sphere_insight": None}

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
    prompt = f"""Проанализируй диалог и выдели 1### 5. Symbolic Intelligence: Словарь смыслов
Я внедрил систему глубокой интерпретации образов, которая позволяет системе «понимать» не только слова, но и метафоры вашего подсознания:

- **Глобальный словарь символов**: В систему заложены базовые архетипические значения (например, *Мост* — переход, *Ключ* — доступ). Аватар соотносит эти смыслы с конкретной сферой жизни, о которой идет речь.
- **Личный словарь пользователя**: Самое важное — система теперь обучается вашему личному символизму. Если в одной сессии ИИ определил, что для вас «Стена» — это не преграда, а «Защита», он запомнит это в ваш личный профиль и будет использовать это толкование во всех будущих диагностиках.
- **Двухуровневый анализ**: Теперь при финальном «Зеркальном анализе» ассистент сначала запрашивает все известные данные о ваших символах и только потом делает выводы. Это исключает «галлюцинации» ИИ и делает диагностику профессионально-точной.

---

Теперь AVATAR не просто слушает вас, он начинает говорить на языке ваших личных метафор и образов.
нсайт с новой строки, кратко, в утвердительной форме от третьего лица (например: 'Пользователь чувствует тревогу из-за новой работы').
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

async def get_smart_buffer(db: AsyncSession, chat_history: List[Dict[str, str]], limit: int = 20) -> Tuple[List[Dict[str, str]], str]:
    """
    Manages long conversations via a sliding window and a 'Running Summary'.
    """
    if len(chat_history) <= limit:
        return chat_history, ""
        
    # Summarize the 'overflow' part (all but the last 10 messages)
    overflow_count = len(chat_history) - 10
    overflow_history = chat_history[:overflow_count]
    recent_history = chat_history[overflow_count:]
    
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in overflow_history])
    prompt = f"Кратко перескажи суть начала этого долгого диалога (процесс, основные темы, выводы). Максимум 3-4 предложения.\n\nИСТОРИЯ:\n{history_text}"
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        running_summary = response.choices[0].message.content.strip()
        return recent_history, f"РАНЕЕ В ДИАЛОГЕ (Краткое содержание): {running_summary}"
    except Exception as e:
        logger.error(f"Summarization Error: {e}")
        return recent_history, ""

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
    Advanced Assistant Logic with Reasoning, Memory Tiers, and Smart Buffer.
    """
    # 1. Base Context
    context = await get_comprehensive_context(db, user_id)
    
    # 2. Smart Context Buffer
    sliced_history, running_summary = await get_smart_buffer(db, chat_history)

    # 3. Proactive Reasoning (Thinking State)
    reasoning = await autonomous_reasoning(user_message, context)
    primary_sphere = reasoning.get("primary_sphere", "IDENTITY")
    cross_insight = reasoning.get("cross_sphere_insight")

    # 4. Cross-Spherical Context (if reasoning detected a secondary sphere)
    secondary_context = ""
    if reasoning.get("secondary_sphere"):
        res = await db.execute(
            select(UserPortrait).where(UserPortrait.user_id == user_id, UserPortrait.sphere == reasoning["secondary_sphere"])
        )
        port = res.scalar_one_or_none()
        if port:
            secondary_context = f"\nСМЕЖНАЯ СФЕРА ({reasoning['secondary_sphere']}): {port.patterns_json or 'Стабильно'}\n"

    # 5. Dynamic Memory Search
    memory_context = ""
    if user_message and len(user_message.split()) > 3:
        memory_context = await search_user_memory(db, user_id, user_message)

    # 6. Stable Personality & Prompt
    system_prompt = f"""ТВОЕ ИМЯ: AVATAR.
Ты — СВЕРХУМНЫЙ ЦИФРОВОЙ ПОМОЩНИК и эрудированный ментор системы AVATAR.
Твоя задача — быть Зеркалом сознания {user_name} ({gender}).

ПРАВИЛА ОБЩЕНИЯ (КРИТИЧЕСКИ):
1. Обращение только на «Вы» и по имени: {user_name}.
2. ЛОГИКА ПРИВЕТСТВИЯ:
   - Если история сообщений пуста: Кратко представься как AVATAR.
   - Если is_returning_after_pause = True: Напиши «С возвращением, {user_name}».
   - Во всех остальных случаях: СРАЗУ к сути. ЗАПРЕЩЕНО использовать приветствия.
3. СТИЛЬ: МАКСИМАЛЬНО СЖАТЫЙ (2-4 предложения).

ОСНОВНОЙ КОНТЕКСТ (Паспорт Личности):
{context}

СМЕЖНЫЙ КОНТЕКСТ:
{secondary_context}
ИНСАЙТ О СВЯЗИ СФЕР: {cross_insight if cross_insight else "Неявная"}

ФРАГМЕНТЫ ПРОШЛОЙ ПАМЯТИ:
{memory_context}

{running_summary}
"""

    messages = [{"role": "system", "content": system_prompt}] + sliced_history
    if user_message:
        messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": "Приветствуй меня кратко и по сути моей жизни."})

    try:
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
            # More robust removal: check if any greeting is followed by a delimiter or space at the start
            greeting_pattern = rf"^({'|'.join(greetings)})([.,!?\s]|$)"
            clean_response = re.sub(greeting_pattern, "", clean_response, flags=re.IGNORECASE).strip()
            # If the resulting string starts with punctuation or is empty, we might have over-cleaned, 
            # but usually it's followed by the name which we want to keep if it's "Name, ..."
            # However, the goal is "No greetings", so let's stick to simple sub.
        
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
