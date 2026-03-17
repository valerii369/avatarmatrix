import logging
import json
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.rro.base import BaseRiver, RiverOutput
from app.agents.common import client as openai_client, settings
from app.core.manifest_service import ManifestationService


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
        
        current_data = user_print.print_data if user_print else {}
        
        # 2. Prepare context for the Alchemist
        # Convert Pydantic models to serializable dicts
        rivers_json = [r.dict() for r in rivers_data]
        rivers_context = json.dumps(rivers_json, ensure_ascii=False, indent=2)
        
        prompt = f"""
Ты — Верховный Алхимик системы AVATAR. Твоя задача — синтезировать "Паспорт Личности" из разрозненных данных.

ТЕКУЩЕЕ СОСТОЯНИЕ ОКЕАНА:
{json.dumps(current_data, ensure_ascii=False, indent=2)}

НОВЫЕ ДАННЫЕ ОТ РЕК (ИНТЕРПРЕТАЦИИ):
{rivers_context}

ТВОЯ ЗАДАЧА:
Синтезируй глубокий, поэтичный и психологически точный "Паспорт Личности". 
Твой главный фокус — **резонанс между всеми частями портрета**.

ПРАВИЛА ДЛЯ ПАРАМЕТРОВ (portrait_summary):
1. **core_identity**: Это квинтэссенция личности. Ты должен вывести её не только из астрологии, а на основе **всего портрета личности (deep_profile_data)**. Это должно быть 2-3 глубоких предложения, которые объединяют таланты, тени и текущий путь человека.
2. **core_archetype**: Выбери СТРОГО один из 22 классических архетипов (Мажорные Арканы): 
   Шут, Маг, Жрица, Императрица, Император, Жрец, Влюбленные, Колесница, Сила, Отшельник, Колесо Фортуны, Справедливость, Повешенный, Смерть, Умеренность, Дьявол, Башня, Звезда, Луна, Солнце, Суд, Мир.
   Выбор должен резонировать с доминирующими энергиями в deep_profile_data.
3. **energy_type**: Определи доминирующий элемент личности. Выбери СТРОГО один из 5:
   Земля, Вода, Воздух, Огонь, Эфир (Космос).
4. **narrative_role**: Роль человека в его жизненном мифе, исходя из его потенциалов и теней.
5. **current_dynamic**: Главный внутренний фокус или конфликт "здесь и сейчас".

ТРЕБОВАНИЯ К ДАННЫМ:
- Параметры в `portrait_summary` должны быть **идеальным отражением** того, что описано в `deep_profile_data`. 
- `deep_profile_data` должна содержать максимально детальные разборы 12 сфер (spheres_status), используя как фундамент астрологию, так и динамические дополнения из сессий.

ВЕРНИ ОБНОВЛЕННЫЙ ПАСПОРТ В СТРОГОМ JSON:
{{
  "portrait_summary": {{
    "core_identity": "...",
    "core_archetype": "...",
    "energy_type": "...",
    "narrative_role": "...",
    "current_dynamic": "..."
  }},
  "deep_profile_data": {{
    "polarities": {{
      "core_strengths": ["...", "..."],
      "hidden_talents": ["...", "..."],
      "shadow_aspects": ["...", "..."],
      "drain_factors": ["...", "..."]
    }},
    "social_interface": {{
      "worldview_stance": "...",
      "communication_style": "...",
      "karmic_lesson": "..."
    }},
    "spheres_status": {{
      "IDENTITY": {{ 
        "status": "...", 
        "insight": "...",
        "light": "...",
        "shadow": "...",
        "evolutionary_task": "...",
        "life_hacks": ["...", "..."],
        "resonance": 100
      }},
      "RESOURCES": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "COMMUNICATION": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "ROOTS": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "CREATIVITY": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "SERVICE": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "PARTNERSHIP": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "TRANSFORMATION": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "EXPANSION": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "STATUS": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "VISION": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }},
      "SPIRIT": {{ "status": "...", "insight": "...", "light": "...", "shadow": "...", "evolutionary_task": "...", "life_hacks": [], "resonance": 50 }}
    }}
  }},
  "metadata": {{
    "last_river": "name",
    "synthesis_version": "3.2"
  }}
}}
"""
        try:
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            new_ocean_data = json.loads(response.choices[0].message.content)
            
            # 3. Save to Ocean
            if not user_print:
                user_print = UserPrint(user_id=user_id, print_data=new_ocean_data)
                db.add(user_print)
            else:
                user_print.print_data = new_ocean_data
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(user_print, "print_data")
            
            await db.flush()
            
            # 4. Semantic Manifestation: Update Card Matrix via vector search
            await ManifestationService.sync_with_portrait(db, user_id, new_ocean_data)
            
            # 5. Final Senior Atomic Commit!
            await db.commit()
            
            logger.info(f"Ocean and Semantic Manifestation (ATOMIC) updated for user {user_id}")
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
        return obj.print_data if obj else {}
