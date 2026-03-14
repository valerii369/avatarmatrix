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
    async def update_ocean(db: AsyncSession, user_id: int, transcript: str, additional_rivers: Optional[Dict[str, Any]] = None):
        """
        Alchemy Synthesis: Takes raw data (Rivers) and mutates the Ocean (User Print).
        Updated to use the professional synthesis prompt.
        """
        current_ocean = await OceanService.get_ocean(db, user_id)
        current_data_json = current_ocean.model_dump_json() if current_ocean else "{}"
        
        # 1. Primary River: Astrology
        natal_res = await db.execute(select(NatalChart).where(NatalChart.user_id == user_id))
        natal_chart = natal_res.scalar_one_or_none()
        astro_context = "Astro River is dry (no natal chart)."
        if natal_chart:
            astro_context = json.dumps(natal_chart.sphere_descriptions_json, ensure_ascii=False)

        # 2. Secondary Rivers: Session features, user history, etc.
        rivers_context = json.dumps(additional_rivers, ensure_ascii=False) if additional_rivers else "No additional rivers."

        extraction_prompt = f"""
ROLE:
You are the SUPREME AI ALCHEMIST of the AVATAR system. Your task is the Great Work: synthesizing all data flows (Rivers) into a single Ocean (User Print / Personality Passport).

TASK:
1. Analyze the provided input data:
   - CURRENT OCEAN (previous state)
   - RIVER OF STARS (Detailed Synthesis: Interpretation, Light, Shadow, Markers)
   - TECHNICAL RIVERS (Metrics, context)
   - LIVING INFLOW (Transcript of the last session)
2. Extract deep psychological meaning, behavioral patterns, and life scenarios.
3. ALCHEMY RULES:
   - INTEGRATION: Synthesize the "Light" and "Shadow" from the River of Stars into the "Polarities" section of the Ocean.
   - NARRATIVE: Use the "Interpretation" from the River to update the "portrait_summary".
   - NO DUPLICATION: Do not simply copy-paste. Transform into a cohesive, flowing narrative.
4. Fill the required JSON structure, strictly following the UserPrintSchema.

CONSTRAINTS AND RULES (CRITICAL):
1. NO JARGON: Completely exclude technical astrology terms.
2. OBJECTIVITY: Maintain balanced analytical tone. Accurately reflect both talents/strengths and shadows/fears without judgment.
3. CONCISENESS: Dense, informative values. No fluff or cliches.
4. STRICT JSON OUTPUT: Output ONLY valid JSON. No markdown blocks.
5. NO HALLUCINATIONS: Fill fields only based on provided data.

CURRENT OCEAN (For continuity):
{current_data_json}

RIVER OF STARS (Astrology - 12 Spheres):
{astro_context}

TECHNICAL INFLOWS:
{rivers_context}

LIVING INFLOW (Session):
{transcript}

RETURN COMPLETE JSON according to UserPrintSchema:
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
                messages=[{"role": "system", "content": extraction_prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            new_data_raw = json.loads(response.choices[0].message.content)
            validated_ocean = UserPrintSchema(**new_data_raw)
            
            # Save to DB
            result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
            up_model = result.scalar_one_or_none()
            if not up_model:
                up_model = UserPrint(user_id=user_id)
                db.add(up_model)
            
            up_model.print_data = validated_ocean.model_dump()
            await db.commit()
            logger.info(f"Ocean (User Print) synthesized for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error in Ocean Synthesis: {e}")
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
