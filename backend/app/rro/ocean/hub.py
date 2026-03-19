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
        from app.models.identity_passport import IdentityPassport
        from sqlalchemy import select

        # 1. Fetch current Ocean state
        res = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        user_print = res.scalar_one_or_none()
        
        current_print = user_print.print_data if user_print else {
            "portrait_summary": {},
            "deep_profile_data": {"spheres_status": {}, "polarities": {}, "social_interface": {}},
            "metadata": {"synthesis_version": "3.3"}
        }
        
        # 2. Fetch Identity Passport (L2)
        passport_res = await db.execute(select(IdentityPassport).where(IdentityPassport.user_id == user_id))
        passport = passport_res.scalar_one_or_none()
        
        if not passport or not passport.aggregated_data:
            logger.warning(f"No Passport data for user {user_id}, skipping L3 synthesis.")
            return
            
        # 3. Aggregated Data for LLM
        # We take the astrology channel specifically as requested for now
        astro_data = passport.aggregated_data.get("astrology", {}).get("data", {})
        new_spheres = astro_data.get("spheres", {})
        
        current_print["deep_profile_data"]["spheres_status"] = new_spheres

        # 4. Call the Alchemist for L3 Simplification & Global Synthesis
        prompt = f"""
Ты — Верховный Алхимик AVATAR. Твоя задача — ПОЛНОЕ УПРОЩЕНИЕ (LVL 3) данных для Паспорта Личности.
Используй детальные интерпретации сфер и создай краткий, но глубокий профиль.

ДАННЫЕ ПО СФЕРАМ:
{json.dumps(new_spheres, ensure_ascii=False, indent=2)}

ТВОЯ ЗАДАЧА:
1. Создай **characteristics**: 5-7 ключевых характеристик личности. 
   Формат: "название характеристики": "краткое описание (2-3 ПРЕДЛОЖЕНИЯ)".
2. Создай **spheres_brief**: Краткое резюме для каждой из 12 сфер.
   Формат: "НАЗВАНИЕ_СФЕРЫ": "краткое описание (2-3 ПРЕДЛОЖЕНИЯ)".
3. Синтезируй **portrait_summary**: Квинтэссенция (core_identity), Архетип (core_archetype — один из 22 арканов), Роль (narrative_role).

ЯЗЫК: СТРОГО РУССКИЙ.
ОТВЕТЬ В СТРОГОМ JSON:
{{
  "characteristics": {{
    "Название 1": "Описание 2-3 предложения...",
    "Название 2": "Описание 2-3 предложения..."
  }},
  "spheres_brief": {{
    "IDENTITY": "...",
    "RESOURSES": "...",
    ... (все 12 сфер)
  }},
  "portrait_summary": {{
    "core_identity": "...",
    "core_archetype": "...",
    "narrative_role": "..."
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
            
            # 5. Integrate L3 Synthesis back into the Passport
            passport.simplified_characteristics = synthesis.get("characteristics", {})
            raw_spheres_brief = synthesis.get("spheres_brief", {})
            
            # Build FULL sphere records: L2 complete data + L3 summary injected on top
            # This preserves all fields: status, about, insight, light, shadow,
            # evolutionary_task, life_hacks, astrological_markers, resonance, weighted_resonance
            enriched_spheres_brief = {}
            for sphere_key in new_spheres:
                l2_sphere = dict(new_spheres.get(sphere_key, {}))   # full L2 copy
                l3_value  = raw_spheres_brief.get(sphere_key, "")
                # Inject L3 condensed summary alongside L2 richness
                if isinstance(l3_value, str):
                    l2_sphere["summary"] = l3_value
                elif isinstance(l3_value, dict):
                    l2_sphere.update(l3_value)   # merge, L3 wins on conflicts
                enriched_spheres_brief[sphere_key] = l2_sphere
            
            # Also add any spheres that L3 returned but weren't in L2 (edge case)
            for sphere_key, l3_value in raw_spheres_brief.items():
                if sphere_key not in enriched_spheres_brief:
                    enriched_spheres_brief[sphere_key] = (
                        l3_value if isinstance(l3_value, dict) else {"summary": l3_value}
                    )
            
            passport.spheres_brief = enriched_spheres_brief
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(passport, "simplified_characteristics")
            flag_modified(passport, "spheres_brief")
            
            # 6. Update User Print for backward compatibility (Portrait View)
            current_print["portrait_summary"] = synthesis.get("portrait_summary", {})
            # We keep spheres_status as detailed data, but simplified_characteristics for hub view
            current_print["metadata"]["last_update"] = "alchemist_l3_passport"
            current_print["metadata"]["synthesis_version"] = "4.0"

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
            await ManifestationService.sync_with_portrait(db, user_id, current_print)
            
            # 7.5. Auto-vectorize passport for RAG semantic search
            from app.rro.passport_service import PassportService
            await PassportService.vectorize_passport(db, user_id)
            
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
