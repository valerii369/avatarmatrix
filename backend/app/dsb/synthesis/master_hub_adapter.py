from __future__ import annotations
"""
Master Hub Adapter — Мост между новым DSB пайплайном и старым фронтендом.

Фронтенд ожидает объект UserPrint для валидации вкладки "О тебе" (Master Hub).
Этот адаптер берет данные от Compressor и MetaAgent и формирует синтетический
UserPrint-объект, чтобы UI отображался корректно, а внутри UI уже загружались
детальные карточки прямо из DSB-таблиц.
"""

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
    meta_patterns: dict
) -> None:
    """
    Создает или обновляет запись UserPrint на основе данных от DSB.
    """
    try:
        # Парсим overall_brief для core_identity
        overall_text = brief.get("overall_brief", "Анализ завершен. Добро пожаловать.")
        
        # Парсим топ-метапаттерн для кармического урока
        top_meta = ""
        if meta_patterns and "meta_patterns" in meta_patterns and len(meta_patterns["meta_patterns"]) > 0:
            top_meta = meta_patterns["meta_patterns"][0].get("name", "") + ": " + meta_patterns["meta_patterns"][0].get("description", "")
        
        # Формируем структуру, которую ожидает MasterHubView.tsx
        spheres_mapped = {}
        for sphere_id, meta in enumerate(SPHERES_META, 1):
            key = f"sphere_{sphere_id}_brief"
            insight = brief.get(key, "Сфера находится в процессе синтеза...")
            # Пытаемся вытянуть статус из краткого текста (первое предложение)
            status = "Активна"
            if "." in insight:
                status = insight.split(".")[0][:25]
            
            spheres_mapped[meta["key"]] = {
                "status": status,
                "insight": insight
            }

        print_data = {
            "portrait_summary": {
                "core_identity": overall_text,
                "core_archetype": "Многогранная личность (DSB)",
                "narrative_role": "Исследователь (DSB)",
                "energy_type": "Универсальная",
                "current_dynamic": "Интеграция 12 сфер"
            },
            "deep_profile_data": {
                "social_interface": {
                    "worldview_stance": "Синтезированное через DSB",
                    "communication_style": "Прямое и открытое",
                    "karmic_lesson": top_meta[:200] if top_meta else "Исследование себя через все сферы жизни."
                },
                "polarities": {
                    "core_strengths": ["Глубокий анализ", "Осознанность 12 сфер"],
                    "shadow_aspects": ["Стадия интеграции тени"]
                },
                "spheres_status": spheres_mapped,
                "meta_patterns": meta_patterns.get("meta_patterns", []) # Добавляем для вкладки "Портрет"
            }
        }

        # Ищем существующий UserPrint
        result = await session.execute(
            select(UserPrint).where(UserPrint.user_id == user_id)
        )
        user_print = result.scalar_one_or_none()

        if user_print:
            user_print.print_data = print_data
        else:
            user_print = UserPrint(user_id=user_id, print_data=print_data)
            session.add(user_print)
        
        logger.info(f"[DSB Adapter] Synthetic UserPrint saved for user {user_id}")

    except Exception as e:
        logger.error(f"[DSB Adapter] Failed to generate UserPrint: {e}", exc_info=True)
