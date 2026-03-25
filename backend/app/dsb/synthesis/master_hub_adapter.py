from __future__ import annotations
"""
Master Hub Adapter — Мост между новым DSB пайплайном и старым фронтендом.

Фронтенд ожидает объект UserPrint (UserPrintSchema) для вкладки "О тебе" (Master Hub).
Этот адаптер берет данные от Compressor и MetaAgent и формирует синтетический
UserPrint-объект, полностью соответствующий схеме UserPrintSchema.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user_print import UserPrint

logger = logging.getLogger(__name__)

SPHERES_META = [
    {"key": "IDENTITY", "name": "Личность"},
    {"key": "RESOURCES", "name": "Деньги"},
    {"key": "COMMUNICATION", "name": "Связи"},
    {"key": "ROOTS", "name": "Корни"},
    {"key": "CREATIVITY", "name": "Творчество"},
    {"key": "SERVICE", "name": "Служение"},
    {"key": "PARTNERSHIP", "name": "Партнерство"},
    {"key": "TRANSFORMATION", "name": "Тень"},
    {"key": "EXPANSION", "name": "Поиск"},
    {"key": "STATUS", "name": "Статус"},
    {"key": "VISION", "name": "Будущее"},
    {"key": "SPIRIT", "name": "Дух"},
]


async def generate_user_print_from_dsb(
    user_id: int,
    session: AsyncSession,
    brief: dict,
    meta_patterns: dict,
) -> None:
    """
    Создает или обновляет запись UserPrint на основе данных от DSB.
    Структура строго соответствует UserPrintSchema.
    """
    try:
        # ── Парсим overall_brief для core_identity ──────────────────────
        overall_text = brief.get("overall_brief", "Твой DSB Паспорт сформирован. Исследуй 12 сфер.")

        # ── Парсим топ-метапаттерн ───────────────────────────────────────
        raw_patterns = []
        if meta_patterns and "meta_patterns" in meta_patterns:
            raw_patterns = meta_patterns.get("meta_patterns", [])

        top_meta_lesson = "Исследование себя через все сферы жизни."
        if raw_patterns:
            first = raw_patterns[0]
            top_meta_lesson = (first.get("name", "") + ": " + first.get("description", ""))[:500]

        # ── Синтетические сильные/теневые стороны из паттернов ──────────
        core_strengths: list[str] = []
        hidden_talents: list[str] = []
        shadow_aspects: list[str] = []
        drain_factors: list[str] = []

        for pat in raw_patterns[:6]:
            name = pat.get("pattern_name") or pat.get("name", "")
            desc = pat.get("description", "")
            formula = pat.get("formula", "")
            if name:
                core_strengths.append(name)
            if formula:
                hidden_talents.append(formula)
            if desc:
                # First half of patterns → shadow aspects, rest → drain factors
                if len(shadow_aspects) < 3:
                    shadow_aspects.append(desc[:80])
                else:
                    drain_factors.append(desc[:80])

        # Fallback to avoid empty lists (schema requires them)
        if not core_strengths:
            core_strengths = ["Глубокий самоанализ", "Многогранность"]
        if not hidden_talents:
            hidden_talents = ["Системное мышление", "Интуитивное познание"]
        if not shadow_aspects:
            shadow_aspects = ["Интеграция тени (в процессе)"]
        if not drain_factors:
            drain_factors = ["Перфекционизм в саморазвитии"]

        # ── Формируем spheres_status ─────────────────────────────────────
        spheres_mapped: dict = {}
        for sphere_id, meta in enumerate(SPHERES_META, 1):
            key = f"sphere_{sphere_id}_brief"
            insight = brief.get(key, f"Сфера «{meta['name']}» находится в процессе синтеза...")
            # Первое предложение как статус (обрезаем до 30 символов)
            status = "В синтезе"
            if insight and "." in insight:
                status = insight.split(".")[0][:30].strip()

            spheres_mapped[meta["key"]] = {
                "status": status,
                "insight": insight,
                "light": None,
                "shadow": None,
                "evolutionary_task": None,
                "life_hacks": [],
                "resonance": 60,
            }

        # ── Итоговый print_data (строгое соответствие UserPrintSchema) ───
        print_data = {
            "portrait_summary": {
                "core_identity": overall_text,
                "core_archetype": "Многогранная личность",
                "narrative_role": "Исследователь",
                "energy_type": "Универсальная",
                "current_dynamic": "Интеграция 12 сфер",
            },
            "deep_profile_data": {
                "social_interface": {
                    "worldview_stance": "Целостный взгляд, синтезированный через DSB",
                    "communication_style": "Прямое и осознанное",
                    "karmic_lesson": top_meta_lesson,
                },
                "polarities": {
                    "core_strengths": core_strengths[:5],
                    "hidden_talents": hidden_talents[:5],
                    "shadow_aspects": shadow_aspects[:5],
                    "drain_factors": drain_factors[:5],
                },
                "spheres_status": spheres_mapped,
                "meta_patterns": raw_patterns,
            },
            "metadata": {
                "source": "dsb_pipeline",
                "version": "2.0",
            },
        }

        # ── Сохраняем/обновляем UserPrint ───────────────────────────────
        result = await session.execute(
            select(UserPrint).where(UserPrint.user_id == user_id)
        )
        user_print = result.scalar_one_or_none()

        if user_print:
            user_print.print_data = print_data
        else:
            user_print = UserPrint(user_id=user_id, print_data=print_data)
            session.add(user_print)

        logger.info(f"[DSB Adapter] UserPrint saved for user {user_id}")

    except Exception as e:
        logger.error(f"[DSB Adapter] Failed to generate UserPrint: {e}", exc_info=True)
