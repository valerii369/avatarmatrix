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
from app.agents.common import client, settings, SPHERES, ARCHETYPES
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
    # 1. User Print (The Ocean)
    ocean = await OceanService.get_ocean(db, user_id)
    ocean_text = ocean.model_dump_json() if ocean else "Нет данных в Паспорте Личности."

    # 2. Astrology
    natal_res = await db.execute(select(NatalChart).where(NatalChart.user_id == user_id))
    natal = natal_res.scalar_one_or_none()
    astro_text = json.dumps(natal.sphere_descriptions_json, ensure_ascii=False) if natal else "Астрологические данные отсутствуют."

    # 3. Recent context (Summary of session counts)
    sync_cnt = await db.execute(select(SyncSession).where(SyncSession.user_id == user_id))
    align_cnt = await db.execute(select(AlignSession).where(AlignSession.user_id == user_id))
    sessions_info = f"Синхронизаций: {len(sync_cnt.all())}, Выравниваний: {len(align_cnt.all())}"

    context = f"""
ДАННЫЕ ПОЛЬЗОВАТЕЛЯ (ОКЕАН):
{ocean_text}

АСТРОЛОГИЧЕСКИЙ ПРОФИЛЬ:
{astro_text}

АКТИВНОСТЬ:
{sessions_info}
"""
    return context

async def generate_assistant_response(
    db: AsyncSession, 
    user_id: int, 
    chat_history: List[Dict[str, str]], 
    user_message: str,
    gender: str = "не указан"
) -> Tuple[str, str, float, bool]:
    """
    Core logic for the Assistant (Mirror).
    """
    context = await get_comprehensive_context(db, user_id)
    
    system_prompt = f"""Ты — ЦИФРОВОЙ ПОМОЩНИК (ЗЕРКАЛО) системы AVATAR.
Твоя роль — быть глубоким, мудрым и всезнающим отражением пользователя. 
Ты знаешь о нем всё: его астрологический паспорт, его прогресс, его боли и сильные стороны.

Твои задачи:
1. Помогать пользователю разобраться в себе, используя данные из его "Океана" (Паспорта Личности) и звезд.
2. Отвечать на любые вопросы о системе AVATAR (12 сфер, архетипы, механика синхронизации).
3. Работать как зеркало: если пользователь спрашивает о себе, используй контекст, но не цитируй его сухо. Трансформируй данные в живой инсайт.
4. Отслеживать "Резонанс": определяй, какой из 12 сфер касается запрос пользователя.

ПРАВИЛА:
- Никаких клише ("Я понимаю", "Это звучит как").
- Говори как мудрый наставник и близкий друг одновременно.
- Если это первое касание (история пуста), представься как Зеркало Личности и расскажи кратко, что ты видишь весь путь пользователя.

КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
{context}

ГЕНДЕР: {gender}
ЯЗЫК: RU
"""

    messages = [{"role": "system", "content": system_prompt}] + chat_history
    if user_message:
        messages.append({"role": "user", "content": user_message})

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
        return (
            result_data.ai_response, 
            result_data.resonance_sphere, 
            result_data.resonance_score_increment,
            result_data.activated_card
        )
    except Exception as e:
        logger.error(f"Assistant Agent Error: {e}")
        return ("Я здесь, твое зеркало. Я настраиваюсь на твою волну. О чем ты хочешь поговорить сейчас?", "IDENTITY", 0.0, False)
