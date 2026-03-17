import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_print import UserPrint
from app.models.natal_chart import NatalChart
from app.schemas.user_print import (
    UserPrintSchema, PortraitSummary, DeepProfileData, 
    Polarities, SocialInterface, SphereStatus
)
from app.agents.common import client, settings

logger = logging.getLogger(__name__)

class OceanService:
    """
    THE OCEAN: Unified management of the User's Digital Avatar (Master Hub / User Print).
    This service handles synthesis from disparate 'Rivers' into a cohesive narrative.
    """

    @staticmethod
    async def get_ocean(db: AsyncSession, user_id: int) -> Optional[UserPrintSchema]:
        """Fetch the current state of the Ocean (User Print) from the database."""
        result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        up_model = result.scalar_one_or_none()
        if up_model:
            try:
                return UserPrintSchema(**up_model.print_data)
            except Exception as e:
                logger.warning(f"Failed to parse old Ocean data for user {user_id}: {e}")
                return None
        return None

    @staticmethod
    async def build_context(db: AsyncSession, user_id: int, target_sphere: Optional[str] = None) -> str:
        """
        Generates a token-efficient system prompt context from the Ocean.
        """
        ocean = await OceanService.get_ocean(db, user_id)
        if not ocean:
            return ""

        ps = ocean.portrait_summary
        lines = [f"USER_BOOK_CONTEXT (The Ocean): Identity: {ps.core_identity} | Role: {ps.narrative_role} | Archetype: {ps.core_archetype}"]
        
        dp = ocean.deep_profile_data
        if dp.polarities.core_strengths:
            lines.append(f"STRENGTHS: {', '.join(dp.polarities.core_strengths[:3])}")
        
        if target_sphere and target_sphere in dp.eight_spheres_status:
            s = dp.eight_spheres_status[target_sphere]
            lines.append(f"FOCUS_CHAPTER ({target_sphere}): {s.insight}")
        else:
            # Summary of top active spheres
            active = [f"{k}:{v.status}" for k, v in list(dp.eight_spheres_status.items())[:3]]
            if active:
                lines.append(f"ACTIVE_CHAPTERS: {', '.join(active)}")

        return "\n".join(lines) + "\nSpeak to the soul using this narrative. Do not mention labels.\n"

    @staticmethod
    async def update_ocean(db: AsyncSession, user_id: int, rivers_data: List[Dict[str, Any]]):
        """
        THE OCEAN SYNTHESIS (Level 3): 
        Acts as the 'Grand Alchemist' Hub. 
        Takes processed interpretations (Rivers) and mutates the Ocean (User Print).
        """
        current_ocean = await OceanService.get_ocean(db, user_id)
        current_data_json = current_ocean.model_dump_json() if current_ocean else "{}"
        
        # Consolidate all river data into a single context for the Alchemist
        consolidated_rivers = json.dumps(rivers_data, ensure_ascii=False)

        synthesis_prompt = f"""
РОЛЬ:
Ты — ВЕРХОВНЫЙ АЛХИМИК системы AVATAR (Уровень 3: Океан). 
Твоя задача — Великое Делание: финальный синтез СМЫСЛОВ из различных потоков (Рек) в единый Океан (Портрет Пользователя / Паспорт Личности).

ВХОДНЫЕ ДАННЫЕ (РЕКИ):
{consolidated_rivers}

ТЕКУЩЕЕ СОСТОЯНИЕ ОКЕАНА (Для преемственности):
{current_data_json}

ЗАДАЧА:
1. Проанализируй интерпретации от различных узкоспециализированных агентов (Астрологи, Нумерологи и т.д.).
2. Создай цельный, глубокий психологический портрет, устраняя противоречия и находя скрытые связи между учениями.
3. ПРАВИЛА АЛХИМИИ (L3):
   - ИНТЕГРАЦИЯ: Объедини сильные стороны и тени из всех Рек в раздел «Polarities».
   - НАРРАТИВ: Сформируй единую «core_identity» (СТРОГО МАКСИМУМ 100 СИМВОЛОВ) — самую суть на стыке всех учений.
   - СФЕРЫ: Для каждой из 12 сфер жизни напиши финальный, глубочайший «insight» (8-10 предложений), вобравший в себя мудрость всех предоставленных Рек.
   - СТИЛЬ: Без технического жаргона. Живой, текучий, проникающий в самую суть.

ОГРАНИЧЕНИЯ:
1. БЕЗ ЖАРГОНА: Полностью исключи астрологические или нумерологические термины. Только смыслы.
2. ЯЗЫК: СТРОГО на РУССКОМ языке.
3. ВЫВОД: ТОЛЬКО валидный JSON согласно схеме.

ВЕРНИ ПОЛНЫЙ JSON согласно UserPrintSchema:
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
      "core_strengths": [],
      "hidden_talents": [],
      "shadow_aspects": [],
      "drain_factors": []
    }},
    "social_interface": {{
      "worldview_stance": "...",
      "communication_style": "...",
      "karmic_lesson": "..."
    }},
    "spheres_status": {{
      "IDENTITY": {{ "status": "...", "insight": "..." }},
      "RESOURCES": {{ "status": "...", "insight": "..." }},
      "COMMUNICATION": {{ "status": "...", "insight": "..." }},
      "ROOTS": {{ "status": "...", "insight": "..." }},
      "CREATIVITY": {{ "status": "...", "insight": "..." }},
      "SERVICE": {{ "status": "...", "insight": "..." }},
      "PARTNERSHIP": {{ "status": "...", "insight": "..." }},
      "TRANSFORMATION": {{ "status": "...", "insight": "..." }},
      "EXPANSION": {{ "status": "...", "insight": "..." }},
      "STATUS": {{ "status": "...", "insight": "..." }},
      "VISION": {{ "status": "...", "insight": "..." }},
      "SPIRIT": {{ "status": "...", "insight": "..." }}
    }}
  }}
}}
"""
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": synthesis_prompt}],
                response_format={"type": "json_object"}
            )
            
            new_data_raw = json.loads(response.choices[0].message.content)
            validated_ocean = UserPrintSchema(**new_data_raw)
            
            # Save/Update in DB
            result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
            up_model = result.scalar_one_or_none()
            if not up_model:
                up_model = UserPrint(user_id=user_id)
                db.add(up_model)
            
            up_model.print_data = validated_ocean.model_dump()
            await db.commit()
            logger.info(f"Level 3 Ocean synthesis completed for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error in Level 3 Ocean Synthesis: {e}")
            return False


    @staticmethod
    async def initialize_from_astro(db: AsyncSession, user_id: int, sphere_descriptions: Dict[str, Any]):
        """Creates the initial Ocean state using the full 12-sphere format."""
        spheres_status = {}
        all_spheres = [
            "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS", 
            "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION", 
            "EXPANSION", "STATUS", "VISION", "SPIRIT"
        ]
        
        # Extract from nested "spheres_12" structure
        spheres_data = sphere_descriptions.get("spheres_12", sphere_descriptions)
        
        for s_key in all_spheres:
            details = spheres_data.get(s_key, {})
            # Use 'interpretation' field as the primary insight for the Hub
            insight = details.get("interpretation", "Данные обрабатываются...") if isinstance(details, dict) else details
            
            spheres_status[s_key] = SphereStatus(
                status="Зарождение",
                insight=insight
            )

        # Core ID text synthesis (Placeholder or from available data)
        core_id_text = "Личность, проходящая первичную сонастройку и исследование своего потенциала через систему AVATAR."
        if "IDENTITY" in spheres_data:
            id_details = spheres_data["IDENTITY"]
            if isinstance(id_details, dict) and "interpretation" in id_details:
                core_id_text = id_details["interpretation"]
            elif isinstance(id_details, str):
                core_id_text = id_details

        initial_data = UserPrintSchema(
            portrait_summary=PortraitSummary(
                core_identity=core_id_text,
                core_archetype="Странник",
                energy_type="Нейтральная",
                narrative_role="Герой",
                current_dynamic="Активация потенциала"
            ),
            deep_profile_data=DeepProfileData(
                polarities=Polarities(),
                social_interface=SocialInterface(
                    worldview_stance="Поиск смыслов",
                    communication_style="Наблюдатель",
                    karmic_lesson="Быть собой"
                ),
                spheres_status=spheres_status
            ),
            metadata={"source": "astro_init_v4"}
        )

        result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        up_model = result.scalar_one_or_none()
        if not up_model:
            up_model = UserPrint(user_id=user_id)
            db.add(up_model)
        
        up_model.print_data = initial_data.model_dump()
        await db.commit()
        return True
