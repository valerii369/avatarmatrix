import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_print import UserPrint
from app.models.natal_chart import NatalChart
from app.schemas.user_print import UserPrintSchema, Identity, Psychology, SphereNarrative
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
            return UserPrintSchema(**up_model.print_data)
        return None

    @staticmethod
    async def build_context(db: AsyncSession, user_id: int, target_sphere: Optional[str] = None) -> str:
        """
        Generates a token-efficient system prompt context from the Ocean.
        """
        ocean = await OceanService.get_ocean(db, user_id)
        if not ocean:
            return ""

        lines = [f"USER_BOOK_CONTEXT (The Ocean): Identity: {ocean.identity.summary} | Role: {ocean.identity.narrative_role} | Archetype: {ocean.identity.core_archetype}"]
        
        if ocean.psychology.inner_tensions or ocean.psychology.active_requests:
            lines.append(f"PSY_STATE: Tensions:{ocean.psychology.inner_tensions[:2]} Requests:{ocean.psychology.active_requests[:1]}")

        if target_sphere and target_sphere in ocean.spheres:
            s = ocean.spheres[target_sphere]
            lines.append(f"FOCUS_CHAPTER ({target_sphere}): {s.state_description}")
        else:
            # Summary of top 3 spheres
            active = [f"{k}:{v.evolution_stage}" for k, v in list(ocean.spheres.items())[:3]]
            if active:
                lines.append(f"ACTIVE_CHAPTERS: {', '.join(active)}")

        return "\n".join(lines) + "\nSpeak to the soul using this narrative. Do not mention labels.\n"

    @staticmethod
    async def update_ocean(db: AsyncSession, user_id: int, transcript: str, additional_rivers: Optional[Dict[str, Any]] = None):
        """
        Alchemy Synthesis: Takes raw data (Rivers) and mutates the Ocean (User Print).
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
ТЫ — ВЕРХОВНЫЙ AI-АЛХИМИК СИСТЕМЫ AVATAR.
Твоя задача — Великое Делание: синтезировать все потоки данных (Реки) в единый Океан (User Print).

СТРОГИЕ ПРАВИЛА:
1. НИКАКОГО ЖАРГОНА: Запрещено использовать термины астрологии, HD и т.д.
2. ГЛУБОКОЕ ОПИСАНИЕ: Минимум 5-10 предложений на каждую из 12 сфер жизни.
3. ПОЭТИЧНОСТЬ: Используй метафоры, но оставайся психологически точным.
4. ЛИМИТ IDENTITY: Поле identity.summary должно быть строго до 40 СЛОВ.

ТЕКУЩИЙ ОКЕАН:
{current_data_json}

РЕКА ЗВЕЗД (Астрология):
{astro_context}

ТЕХНИЧЕСКИЕ РЕКИ:
{rivers_context}

ЖИВОЙ ПРИТОК (Сессия):
{transcript}

ВЕРНИ ПОЛНЫЙ JSON по схеме UserPrintSchema (identity, psychology, spheres).
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
            
            # Word count enforcement
            summary_words = validated_ocean.identity.summary.split()
            if len(summary_words) > 40:
                validated_ocean.identity.summary = " ".join(summary_words[:40]) + "..."
            
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
    async def initialize_from_astro(db: AsyncSession, user_id: int, sphere_descriptions: Dict[str, str]):
        """Creates the initial Ocean state from raw astrological data."""
        spheres = {
            code: SphereNarrative(state_description=desc, evolution_stage="Зарождение")
            for code, desc in sphere_descriptions.items()
        }
        
        initial_data = UserPrintSchema(
            identity=Identity(
                summary=sphere_descriptions.get("IDENTITY", "Ваш AVATAR пробуждается..."),
                core_archetype="Странник",
                narrative_role="Герой",
                energy_description="Начальная"
            ),
            psychology=Psychology(),
            spheres=spheres,
            metadata={"source": "astro_init"}
        )

        result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        up_model = result.scalar_one_or_none()
        if not up_model:
            up_model = UserPrint(user_id=user_id)
            db.add(up_model)
        
        up_model.print_data = initial_data.model_dump()
        await db.commit()
        return True
