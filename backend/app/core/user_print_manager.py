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
        Alchemy Engine: Synthesizes technical 'Rivers' (Astro, Sessions, etc.) into the 
        definitive narrative 'Ocean' (User Print).
        """
        current_up = await UserPrintManager.get_user_print(db, user_id)
        current_data_json = current_up.model_dump_json() if current_up else "{}"
        
        # Add NatalChart context (Primary River)
        natal_res = await db.execute(select(NatalChart).where(NatalChart.user_id == user_id))
        natal_chart = natal_res.scalar_one_or_none()
        astro_context = "No natal chart found (Astro River is dry)."
        if natal_chart:
            astro_context = json.dumps(natal_chart.sphere_descriptions_json, ensure_ascii=False)

        # Technical context (Other Rivers)
        rivers_context = json.dumps(source_data, ensure_ascii=False) if source_data else "No additional technical rivers."

        extraction_prompt = f"""
ТЫ — ВЕРХОВНЫЙ AI-АЛХИМИК И ХРАНИТЕЛЬ ОКЕАНА СМЫСЛОВ.
Твоя задача — Великое Делание: принять все потоки данных (Реки) и синтезировать их в единый, неразрывный Океан (User Print).

СТРОГИЕ ЗАКОНЫ АЛХИМИИ (НЕУКОСНИТЕЛЬНО):
1. НИКАКОГО ЖАРГОНА: СТРОЖАЙШЕ ЗАПРЕЩЕНО использовать любые астрологические, нумерологические или технические термины. Никаких "Марсов", "Домов", "Квадратур", "Проекторов", "Манифесторов", "Линий" или "Ворот".
2. ЯЗЫК ОКЕАНА: Используй только живой, глубокий, психологически точный и архетипический язык. Описывай энергию, внутренние конфликты, таланты и ландшафты души так, как если бы ты видел саму суть человека напрямую.
3. МАКСИМАЛЬНАЯ ДЕТАЛИЗАЦИЯ: В описании каждой сферы (state_description) давай максимально развернутую информацию. Минимум 5-10 насыщенных смыслом предложений на каждую сферу. Не жалей токенов — глубина важнее краткости.
4. ГАРМОНИЗАЦИЯ: Найди единую нить, связывающую "Реку Звезд" (астрологию) и "Живую Реку" (сессии). Опиши, как небесные предрасположенности проявляются в конкретном опыте пользователя.
5. СУТЬ ГЕРОЯ (IDENTITY SUMMARY): Сгенерируй предельно плотную, поэтичную и точную выжимку того, кем является этот человек. СТРОГОЕ ОГРАНИЧЕНИЕ: НЕ БОЛЕЕ 40 СЛОВ. Это должен быть "кристалл" всей личности.

ТЕКУЩИЙ ОКЕАН (Hub):
{current_data_json}

РЕКА ЗВЕЗД (Астрологический базис):
{astro_context}

ТЕХНИЧЕСКАЯ РЕКА (Дополнительные данные):
{rivers_context}

ЖИВОЙ ПРИТОК (Транскрипт сессии):
{transcript}

ПРОЦЕСС ТРАНСМУТАЦИИ:
1. IDENTITY: Обнови облик Героя.
   - summary: Краткая суть (МАКСИМУМ 40 СЛОВ).
   - core_archetype: Доминирующий архетип.
   - narrative_role: Роль в сюжете.
   - energy_description: Энергетический почерк.
2. PSYCHOLOGY: Глубинные маркеры (мысли, таланты, ограничения, телесные якоря).
3. SPHERES: 12 глав Книги Жизни. Для КАЖДОЙ из 12 сфер (IDENTITY, RESOURCES, COMMUNICATION, ROOTS, CREATIVITY, SERVICE, PARTNERSHIP, TRANSFORMATION, EXPANSION, STATUS, VISION, SPIRIT) создай максимально подробное описание (state_description).

ВЕРНИ ПОЛНЫЙ JSON, строго по схеме UserPrintSchema.
"""

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": extraction_prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            new_data_raw = json.loads(response.choices[0].message.content)
            
            # Validate with Pydantic
            validated_up = UserPrintSchema(**new_data_raw)
            
            # Post-processing: Ensure identity summary is within limits
            summary_words = validated_up.identity.summary.split()
            if len(summary_words) > 40:
                validated_up.identity.summary = " ".join(summary_words[:40]) + "..."
                
            new_data = validated_up.model_dump()
            
            # 3. Save to database
            result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
            up_model = result.scalar_one_or_none()
            
            if not up_model:
                up_model = UserPrint(user_id=user_id)
                db.add(up_model)
            
            up_model.print_data = new_data
            await db.commit()
            
            logger.info(f"Ocean (User Print) synthesized for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error synthesizing Ocean: {e}")
            return False

    @staticmethod
    async def initialize_from_astro(db: AsyncSession, user_id: int, sphere_descriptions: Dict[str, str]):
        """
        Quickly creates an initial User Print from raw astrological descriptions.
        This provides immediate feedback to the user before the Alchemist refines it.
        """
        # 1. Prepare SphereNarratives
        spheres = {}
        for code, desc in sphere_descriptions.items():
            spheres[code] = {
                "state_description": desc,
                "evolution_stage": "Зарождение (Астро)"
            }

        # 2. Build initial structure
        initial_data = {
            "identity": {
                "summary": sphere_descriptions.get("IDENTITY", "Ваш AVATAR пробуждается..."),
                "core_archetype": "В поиске...",
                "narrative_role": "Странник",
                "energy_description": "Формирующаяся",
                "archetypal_resonance": {}
            },
            "psychology": {
                "guiding_thoughts": [],
                "active_requests": [],
                "inner_tensions": [],
                "talents": [],
                "limitations": [],
                "somatic_anchors": []
            },
            "spheres": spheres,
            "metadata": {"initial_sync": "astro"}
        }

        # 3. Save to database
        result = await db.execute(select(UserPrint).where(UserPrint.user_id == user_id))
        up_model = result.scalar_one_or_none()
        
        if not up_model:
            up_model = UserPrint(user_id=user_id)
            db.add(up_model)
        
        up_model.print_data = initial_data
        await db.commit()
        logger.info(f"Ocean (User Print) initialized from Astro for user {user_id}")
        return True
