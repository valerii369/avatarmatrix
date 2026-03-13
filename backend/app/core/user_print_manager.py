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

ПРАВИЛА ТРАНСМУТАЦИИ:
1. ОКЕАН — ЕДИНСТВЕННЫЙ ИСТОЧНИК: Твоя цель — создать настолько полное и глубокое описание, чтобы пользователю больше не нужно было смотреть на "технические реки" (астрологию или отчеты сессий).
2. НИКАКИХ ТЕХНИЧЕСКИХ ТЕРМИНОВ: Забудь про 'Марс', 'Квадратуру', 'Проектора'. Используй только живой, психологически точный и архетипический язык («внутренний огонь», «зов к переменам», «теневые границы»).
3. ГАРМОНИЗАЦИЯ: Если данные из разных рек (например, астрологии и живого разговора) кажутся разными — найди ГЛУБИННУЮ СВЯЗЬ. Речь идет об одном и том же человеке в разных контекстах.
4. UPSERT: Обогащай текущий Океан новыми деталями, не теряя глубины прошлых открытий.

ТЕКУЩИЙ ОКЕАН (Hub):
{current_data_json}

РЕКА ЗВЕЗД (Астрологический базис):
{astro_context}

ТЕХНИЧЕСКАЯ РЕКА (Дополнительные данные):
{rivers_context}

ЖИВОЙ ПРИТОК (Транскрипт сессии):
{transcript}

ПРОЦЕСС:
1. IDENTITY: Обнови суть Героя.
   - summary: Глубинное описание (минимум 3-5 предложений).
   - core_archetype: Доминирующий архетип.
   - narrative_role: Текущая роль в жизненном сюжете.
   - energy_description: Как человек звучит энергетически.
   - archetypal_resonance: Отношение к ключевым силам (Власть, Любовь, Тень, Свобода).
2. PSYCHOLOGY: 
   - Выяви SOMATIC ANCHORS (телесные якоря).
   - Сформулируй guiding_thoughts, talents (таланты), limitations (ограничения), active_requests (запросы).
3. SPHERES (12 глав Книги Жизни): Опиши состояние в каждой сфере (IDENTITY, RESOURCES, COMMUNICATION, ROOTS, CREATIVITY, SERVICE, PARTNERSHIP, TRANSFORMATION, EXPANSION, STATUS, VISION, SPIRIT).
   - state_description: Живой ландшафт сферы (3-7 предложений).
   - evolution_stage: Стадия (напр. 'Зарождение', 'Кризис', 'Расцвет', 'Трансформация').
   - key_lesson: Текущий вызов или урок.

ВЕРНИ ПОЛНЫЙ JSON, строго по схеме UserPrintSchema. Заполни ВСЕ обязательные поля.
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
