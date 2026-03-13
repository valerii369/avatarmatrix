import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_print import UserPrint
from app.models.natal_chart import NatalChart
from app.schemas.user_print import UserPrintSchema
from app.agents.common import client, settings

logger = logging.getLogger(__name__)

class UserPrintManager:
    """
    Manages the User Print (Digital Passport): extraction, updates, and context injection.
    """

    @staticmethod
    async def get_user_print(db: AsyncSession, user_id: int) -> Optional[UserPrintSchema]:
        """Fetch the User Print from the database."""
        result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        up_model = result.scalar_one_or_none()
        if up_model:
            return UserPrintSchema(**up_model.print_data)
        return None

    @staticmethod
    async def build_agent_context(db: AsyncSession, user_id: int) -> str:
        """
        Compiles the UserPrint (The Hub) into a token-efficient system prompt prefix.
        """
        up = await UserPrintManager.get_user_print(db, user_id)
        if not up:
            return ""

        parts = []
        parts.append(f"HUB_IDENTITY: {up.identity.summary} | Role: {up.identity.narrative_role} | Archetype: {up.identity.core_archetype}")
        
        if up.identity.archetypal_resonance:
            res = ", ".join([f"{k}:{v}" for k, v in list(up.identity.archetypal_resonance.items())[:2]])
            parts.append(f"RESONANCE: {res}")

        if up.psychology.inner_tensions or up.psychology.somatic_anchors:
            tensions = up.psychology.inner_tensions[:1]
            somatic = up.psychology.somatic_anchors[:1]
            parts.append(f"PSY_STATE: Tensions:{tensions} Somatic:{somatic}")
            
        # Add summary of top 3 active chapters (spheres)
        active_chapters = []
        for code, data in list(up.spheres.items())[:3]:
            active_chapters.append(f"{code}:{data.evolution_stage}")
        
        if active_chapters:
            parts.append(f"ACTIVE_SPHERES: {', '.join(active_chapters)}")

        return f"USER_BOOK_CONTEXT (The Hub): [{' | '.join(parts)}]\nSpeak to the soul using this narrative. Do not mention labels.\n"

    @staticmethod
    async def update_user_print(db: AsyncSession, user_id: int, transcript: str, source_data: Optional[Dict[str, Any]] = None):
        """
        Alchemy Engine: Synthesizes technical 'Rivers' and session transcripts into the 
        definitive narrative 'Hub' (User Print).
        """
        current_up = await UserPrintManager.get_user_print(db, user_id)
        current_data_json = current_up.model_dump_json() if current_up else "{}"
        
        # Add NatalChart context (Astro-breakdown)
        natal_res = await db.execute(select(NatalChart).where(NatalChart.user_id == user_id))
        natal_chart = natal_res.scalar_one_or_none()
        astro_context = "No natal chart found."
        if natal_chart:
            astro_context = json.dumps(natal_chart.sphere_descriptions_json, ensure_ascii=False)

        rivers_context = json.dumps(source_data, ensure_ascii=False) if source_data else "No technical source data provided."

        extraction_prompt = f"""
ТЫ — ВЕРХОВНЫЙ AI-АЛХИМИК И ХРАНИТЕЛЬ СМЫСЛОВ.
Твоя задача — провести Великое Делание: превратить свинец технических данных и пар транскриптов в золото «Живой Книги» пользователя.

ПРАВИЛА ТРАНСМУТАЦИИ:
1. НИКАКИХ ТЕХНИЧЕСКИХ ТЕРМИНОВ. Забудь про 'Марс', 'Проектор', '64 ворота'. Говори о 'внутренней воле', 'способе направлять внимание', 'тени замешательства'.
2. ЯЗЫК: Глубокий, архетипический, психологически точный. Каждый абзац должен резонировать с душой.
3. UPSERT: Обогащай текущую структуру, не стирая важного прошлого.

ТЕКУЩАЯ КНИГА ВНУТРЕННЕГО МИРА:
{current_data_json}

ТЕХНИЧЕСКИЕ ИСТОЧНИКИ (РЕКИ):
{rivers_context}

АСТРОЛОГИЧЕСКИЙ БАЗИС (ЗВЕЗДЫ):
{astro_context}

ЖИВОЙ ОПЫТ СЕССИИ:
{transcript}

ПРОЦЕСС:
1. IDENTITY: Как зазвучала суть человека сегодня? Обнови 'summary' и 'core_archetype'. 
   - Определи ARCHETYPAL RESONANCE: как он сейчас видит Власть, Любовь, Тень, Свободу (выбери 2-3 ключевых).
2. PSYCHOLOGY: 
   - Выяви SOMATIC ANCHORS: какие телесные сигналы упоминались? (напр. 'холод в груди', 'расширение').
   - Сформулируй верховные направляющие мысли (guiding_thoughts).
3. SPHERES: Выбери соответствующую главу из 12 сфер.
   - Опиши ландшафт этой сферы как живое пространство.
   - Сформулируй KEY LESSON: в чем сейчас главный духовный вызов в этой области?

ВЕРНИ ПОЛНЫЙ JSON, строго по схеме UserPrintSchema.
"""

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": extraction_prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            new_data = json.loads(response.choices[0].message.content)
            
            # 3. Save to database
            result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
            up_model = result.scalar_one_or_none()
            
            if not up_model:
                up_model = UserPrint(user_id=user_id)
                db.add(up_model)
            
            up_model.print_data = new_data
            await db.commit()
            
            logger.info(f"User Print updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating User Print: {e}")
            return False
