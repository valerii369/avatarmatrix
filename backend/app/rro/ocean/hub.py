import logging
import json
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.rro.base import BaseRiver, RiverOutput
from app.agents.common import client as openai_client, settings

logger = logging.getLogger(__name__)

class OceanService:
    """
    Ocean (Level 3): The Unified Synthesis Hub (The Grand Alchemist).
    Collects interpretations from various Rivers and synthesizes the final User Print.
    """

    @staticmethod
    async def update_ocean(db: AsyncSession, user_id: int, rivers_data: List[RiverOutput]):
        """
        The Hub's main entry point for synthesis.
        Accepts a list of standardized RiverOutput objects.
        """
        from app.models.user_print import UserPrint
        from sqlalchemy import select

        # 1. Fetch current Ocean state
        res = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        user_print = res.scalar_one_or_none()
        
        current_data = user_print.data if user_print else {}
        
        # 2. Prepare context for the Alchemist
        # Convert Pydantic models to serializable dicts
        rivers_json = [r.dict() for r in rivers_data]
        rivers_context = json.dumps(rivers_json, ensure_ascii=False, indent=2)
        
        prompt = f"""
Ты — Верховный Алхимик системы AVATAR. Твоя задача — собрать разрозненные "реки" данных (интерпретации) в единый "Океан" (Паспорт Личности).

ТЕКУЩЕЕ СОСТОЯНИЕ ОКЕАНА:
{json.dumps(current_data, ensure_ascii=False, indent=2)}

НОВЫЕ ДАННЫЕ ОТ РЕК (ИНТЕРПРЕТАЦИИ):
{rivers_context}

ТВОЯ ЗАДАЧА:
1. Интегрировать новые инсайты в существующую структуру.
2. Сгладить противоречия между разными источниками (например, если Астрология говорит одно, а текущая сессия — другое).
3. Обновить Психологический Портрет, Сильные стороны и Тени.
4. Выделить 3 главных фокуса для пользователя на данный момент.

ВЕРНИ ОБНОВЛЕННЫЙ ПАСПОРТ В ФОРМАТЕ JSON (строго по схеме):
{{
  "psychological_portrait": "...",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "behavioral_patterns": ["...", "..."],
  "current_state": "...",
  "recommendations": ["...", "..." ]
}}
"""
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            new_ocean_data = json.loads(response.choices[0].message.content)
            
            # 3. Save to Ocean
            if not user_print:
                user_print = UserPrint(user_id=user_id, data=new_ocean_data)
                db.add(user_print)
            else:
                user_print.data = new_ocean_data
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(user_print, "data")
            
            await db.flush()
            logger.info(f"Ocean updated for user {user_id}")
            return new_ocean_data
            
        except Exception as e:
            logger.error(f"Ocean synthesis failed: {e}")
            return current_data

    @staticmethod
    async def get_ocean(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        from app.models.user_print import UserPrint
        from sqlalchemy import select
        res = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        obj = res.scalar_one_or_none()
        return obj.data if obj else {}
