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
    async def update_ocean(db: AsyncSession, user_id: int):
        """
        The Hub's main entry point for synthesis.
        Strict RRO v2.2+ Logic: Smart Merge (Data Preservation).
        """
        from app.models.user_print import UserPrint
        from app.models.river_result import RiverResult # Import RiverResult
        from sqlalchemy import select

        # 1. Fetch current Ocean state
        res = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        user_print = res.scalar_one_or_none()
        
        current_print = user_print.print_data if user_print else {
            "portrait_summary": {},
            "deep_profile_data": {"spheres_status": {}, "polarities": {}, "social_interface": {}},
            "metadata": {"synthesis_version": "3.3"}
        }
        
        # 2. Fetch all RiverResult entries for the user
        river_results_res = await db.execute(select(RiverResult).where(RiverResult.user_id == user_id))
        all_river_results: List[RiverResult] = river_results_res.scalars().all()

        # 3. Programmatic Sync (Smart Merge) - Merge RiverResult data into current_print
        # We take descriptions from the Rivers and put them into the Ocean structure
        # to prevent LLM hallucinations or data loss.
        new_spheres = current_print["deep_profile_data"].get("spheres_status", {})
        
        for river_result in all_river_results:
            if river_result.domain == "astrology" and "spheres" in river_result.interpretation_data:
                astro_spheres = river_result.interpretation_data["spheres"]
                for s_key, s_data in astro_spheres.items():
                    # Preserve River data exactly (Smart Merge)
                    new_spheres[s_key] = s_data
        
        current_print["deep_profile_data"]["spheres_status"] = new_spheres

        # 4. Call the Alchemist for Global Synthesis (Persona, Role, Global Tone)
        # We ONLY pass what's needed for the global summary to keep prompt focused
        prompt = f"""
Ты — Верховный Алхимик AVATAR. Ты получил данные от "Рек" (глубинные интерпретации сфер жизни).
Твоя задача — создать ЕДИНЫЙ ПОРТРЕТ (Portrait Summary), который объединяет всё это в цельную личность.

ДАННЫЕ ПО СФЕРАМ (УЖЕ СИНТЕЗИРОВАНЫ):
{json.dumps(new_spheres, ensure_ascii=False, indent=2)}

ТВОЯ ЗАДАЧА:
1. Синтезируй **portrait_summary**: Квинтэссенция личности (core_identity), Архетип (core_archetype — СТРОГО один из 22 классических мажорных арканов), Стихия (energy_type), Роль (narrative_role) и Текущий конфликт/динамика (current_dynamic).
2. Синтезируй **polarities**: Сильные стороны, таланты, тени и факторы утечки на основе ВСЕХ сфер.
3. Синтезируй **social_interface**: Мировоззрение, стиль общения и кармический урок.

ВАЖНО: Тебе НЕ НУЖНО переписывать тексты сфер. Сфокусируйся на ОБЩЕМ ПОРТРЕТЕ.
ЯЗЫК: Строго РУССКИЙ.

ОТВЕТЬ В СТРОГОМ JSON:
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
    }}
  }}
}}
"""
        try:
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            synthesis = json.loads(response.choices[0].message.content)
            
            # 5. Integrate Synthesis back into the Print
            current_print["portrait_summary"] = synthesis.get("portrait_summary", {})
            current_print["deep_profile_data"]["polarities"] = synthesis.get("deep_profile_data", {}).get("polarities", {})
            current_print["deep_profile_data"]["social_interface"] = synthesis.get("deep_profile_data", {}).get("social_interface", {})
            current_print["metadata"]["last_update"] = "alchemist_merge"
            current_print["metadata"]["synthesis_version"] = "3.3"

            # 6. Atomic Save
            if not user_print:
                user_print = UserPrint(user_id=user_id, print_data=current_print)
                db.add(user_print)
            else:
                user_print.print_data = current_print
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(user_print, "print_data")
            
            await db.flush()
            
            # 7. Manifestation (Semantic update of CardProgress)
            # This uses the new data to pick archetypes for cards
            await ManifestationService.sync_with_portrait(db, user_id, current_print)
            
            # 8. Final Atomic Commit
            await db.commit()
            
            logger.info(f"Ocean Hub: Smart Merge completed for user {user_id}")
            return current_print

        except Exception as e:
            logger.error(f"Ocean Hub Synthesis failed: {e}")
            await db.rollback()
            return current_print

    @staticmethod
    async def get_ocean(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        from app.models.user_print import UserPrint
        from sqlalchemy import select
        res = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        obj = res.scalar_one_or_none()
        return obj.print_data if obj else {}
