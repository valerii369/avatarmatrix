import logging
import json
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.base_river import BaseRiver
from app.agents.common import client

logger = logging.getLogger(__name__)

class SessionRiver(BaseRiver):
    """
    Session River (Level 2): Interprets general Assistant dialogues (Rain) into user profile updates.
    """
    
    async def flow(self, db: AsyncSession, user_id: int, rain_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw history and returns a summary of psychological/behavioral insights.
        """
        logger.info(f"SessionRiver flowing for user {user_id}")
        
        history = rain_data.get("history", [])
        if not history:
            return {}
            
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        
        prompt = f"""
Проанализируй диалог пользователя с AI-ассистентом.
Твоя задача — извлечь новые факты, психологические паттерны и изменения в состоянии пользователя.

ДИАЛОГ:
{history_text}

ВЕРНИ JSON:
{{
  "session_summary": "Краткое описание сути общения",
  "identified_patterns": ["паттерн 1", "паттерн 2"],
  "emotional_state": "Текущий вайб пользователя",
  "new_user_facts": ["факт 1", "факт 2"]
}}
"""
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            analysis = json.loads(response.choices[0].message.content)
            
            return {
                "source": "session_river",
                "content": analysis,
                "metadata": {"length": len(history)}
            }
        except Exception as e:
            logger.error(f"SessionRiver interpretation failed: {e}")
            return {}
