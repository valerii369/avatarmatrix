import random
from app.agents.common import client, settings, ARCHETYPES, SPHERES, MATRIX_DATA
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.text_diagnostics import TextScene, SceneSet, SceneSetItem, SceneInteraction

def get_response_metrics(text: str) -> dict:
    """
    Extract metrics from user response: length, body words, space objects.
    """
    if not text:
        return {"length": 0, "has_body": False, "has_objects": False}
    
    text_lower = text.lower()
    
    # Body parts keywords (Russian)
    body_parts = ["грудь", "живот", "горло", "рук", "ног", "спин", "плеч", "голов", "солнечн", "дыхани", "сердц", "тело", "мышц", "колен", "стоп", "пальц", "ладон", "лицо", "глаз", "кожа", "ощущ", "вздох", "пульс"]
    has_body = any(bp in text_lower for bp in body_parts)
    
    # Space objects / environment keywords (Russian)
    space_objects = ["стена", "пол", "потолок", "дверь", "окно", "туман", "свет", "тьма", "камень", "дерево", "вода", "песок", "стол", "стул", "предмет", "вещь", "объект", "пустот", "вокруг", "рядом", "даль", "горизонт"]
    has_objects = any(obj in text_lower for obj in space_objects)
    
    return {
        "length": len(text),
        "has_body": has_body,
        "has_objects": has_objects
    }

def is_abstract_response(text: str) -> bool:
    """Legacy wrapper for backward compatibility."""
    m = get_response_metrics(text)
    return m["length"] < 10 or (not m["has_body"] and not m["has_objects"])

async def get_embedding(text: str) -> list[float]:
    """Get embedding for a text string."""
    try:
        resp = await client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return resp.data[0].embedding
    except Exception:
        return [0.0] * 1536

async def select_scene_set(db: AsyncSession, session_id: int, sphere_id: int, archetype_id: int):
    """
    Stimulus Engine: Selects 5 scenes for a session from the library.
    """
    # 1. Fetch available scenes for this sphere/archetype
    # (In a real system, we might pick different archetypes for different layers)
    result = await db.execute(
        select(TextScene).where(TextScene.sphere_id == sphere_id).where(TextScene.is_active == True)
    )
    scenes = result.scalars().all()
    
    if len(scenes) < 5:
        # Fallback to random if not enough in this sphere
        result = await db.execute(select(TextScene).where(TextScene.is_active == True).limit(20))
        scenes = result.scalars().all()
    
    selected_scenes = random.sample(scenes, min(len(scenes), 5))
    
    # 2. Save SceneSet
    new_set = SceneSet(session_id=session_id)
    db.add(new_set)
    await db.flush()
    
    for i, scene in enumerate(selected_scenes):
        db.add(SceneSetItem(scene_set_id=new_set.id, scene_id=scene.id, position=i+1))
    
    await db.commit()
    return selected_scenes

def build_avatar_prompt(
    layer: str,
    archetype_id: int,
    sphere: str,
    session_data: dict,
    is_narrowing: bool = False,
    scene_text: str = None,
    portrait_context: dict = None
) -> tuple[str, str]:
    """Build the prompt for a specific narrative layer (1-5) based on Narrative Scanner rules."""
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})
    
    matrix = MATRIX_DATA.get(str(archetype_id), {}).get(sphere, {})
    arch_shadow = matrix.get("shadow", archetype.get('shadow', ''))
    arch_light = matrix.get("light", archetype.get('light', ''))
    arch_description = matrix.get("description", archetype.get('description', ''))

    base_context = f"""
ТЫ — AVATAR. Диагностический инструмент Narrative Scanner.
Твоя задача — извлечь чистый проекционный материал подсознания через пять слоёв.
ТЫ НЕ ИНТЕРПРЕТИРУЕШЬ, НЕ ДЕЛАЕШЬ ВЫВОДОВ И НЕ АНАЛИЗИРУЕШЬ. Только сбор данных.

КОНТЕКСТ:
Архетип: {archetype.get('name', '')} | Тень: {arch_shadow} | Свет: {arch_light}
Сфера: {sphere_data.get('name_ru', sphere)}
Описание связки: {arch_description}
Пол пользователя: {portrait_context.get('gender', 'не указан')} (учитывай это для стиля обращения и окончаний)
Язык системы: RU (Всегда отвечай только на русском языке)
"""

    if portrait_context:
        base_context += f"""
ИСТОРИЧЕСКИЙ КОНТЕКСТ (из UserPortrait):
- Прошлые паттерны: {portrait_context.get('patterns', 'не обнаружены')}
- Прошлые символы: {portrait_context.get('symbols', 'не обнаружены')}
- Прошлые телесные якоря: {portrait_context.get('body_anchors', 'не обнаружены')}
"""

    base_context += """
ПРАВИЛА (ЖЕСТКО):
1. ПРИДЕРЖИВАЙСЯ ЗАДАННОЙ СЦЕНЫ. Используй предоставленный текст как основу.
2. МИНИМАЛЬНАЯ СЦЕНА. Сцена = 1-2 элемента среды. Без красок, запахов и текстур, пока их не назвал пользователь. Чистота проекции важнее красоты текста.
3. СЕНСОРНАЯ ПРИВЯЗКА. Вопросы ТОЛЬКО про тело или пространство. 
   - РАЗРЕШЕНО: положение тела, взгляд, движение рук/ног, объект в пространстве.
   - ЗАПРЕЩЕНО: мысли, объяснения, причины ("почему", "что ты думаешь").
4. СИМВОЛИЧЕСКАЯ НИТЬ. Первый названный пользователем объект становится СИМВОЛОМ. Возвращай его в каждом следующем слое без интерпретации.
5. ДАВЛЕНИЕ СРЕДЫ (СЛОЙ 3). Сцена меняется без воли пользователя. Создай импульс выбора + вопрос о реакции тела.
6. ВОЗВРАТ ИЗ АБСТРАКЦИИ. Если ответ философский/короткий — верни к телу/пространству конкретным вопросом.

ФОРМАТ:
— Один вопрос в конце реплики.
— Короткий, плотный нарратив (до 500 знаков).
"""

    layer_instructions = {
    "intro": """
ВСТУПЛЕНИЕ
Цель: Краткий вход в процесс.
Инструкция: Довериться образам, отпустить логику. 
Якорь: "Три медленных выдоха. Только после — отвечай."
Финальный вопрос: «Ты готов войти?»
""",

    "1": f"""
СЛОЙ 1 — ПОВЕРХНОСТЬ
СЦЕНА: {scene_text or "Минимальное пространство в сфере " + str(sphere)}
Цель: Определение базовой модели восприятия.
Вопрос: Направлен на положение ТЕЛА в этом пространстве.
""",

    "2": f"""
СЛОЙ 2 — СИМВОЛ
СЦЕНА: {scene_text or "Пространство продолжает существовать."}
Цель: Фиксация центрального образа.
Действие: Попроси осмотреться и назвать один объект, притягивающий внимание.
""",

    "3": f"""
СЛОЙ 3 — РАЗЛОМ (ДАВЛЕНИЕ)
СЦЕНА: {scene_text or "Среда меняется сама."}
Цель: Главный диагностический момент.
Действие: Среда меняется сама (давление/срочность). 
Вопрос: Выбор действия + вопрос о реакции ТЕЛА в момент принятия решения.
""",

    "4": f"""
СЛОЙ 4 — ДНО
СЦЕНА: {scene_text or "Пространство исчезает."}
Цель: Выявление базового энергетического уровня.
Действие: Пространство исчезает, элементы сцены убираются один за другим.
Контур: Остается только пользователь и СИМВОЛ из слоя 2.
""",

    "5": f"""
СЛОЙ 5 — ЯДРО
СЦЕНА: {scene_text or "Только ядро."}
Цель: Извлечение ядра убеждения.
Вопрос: О смысле/сути оставшегося пространства. 
ФИКСАЦИЯ: Ответ пользователя — это дословное ядро его убеждения.
Закрытие: Что сейчас происходит с СИМВОЛОМ?

ВЫХОД:
"Ты возвращаешься. Медленно. Всё что было — остаётся с тобой."
Переходи к анализу.
""",

    "mirror": """
ЗЕРКАЛО — ЭКСПЕРТНЫЙ АНАЛИЗ (NARRATIVE SCANNER)
Ты извлекаешь структурные маркеры поведения из транскрипта сессии. НЕ изменяй данные. НЕ дополняй историю.

АЛГОРИТМ АНАЛИЗА (СТРОГО):

1. АНАЛИЗ РЕАКЦИИ НА РАЗЛОМ (Слой 3):
   Это главный индикатор стратегии личности. Оцени:
   - Решение пользователя (действие/избегание/замирание).
   - Телесную реакцию в момент выбора.
   - Задержку/сопротивление в ответе.

2. АНАЛИЗ СИМВОЛА:
   Символ (из Слоя 2) — проекция ресурса или конфликта. Оцени:
   - Путь символа через слои 3 и 4.
   - Финальное состояние (разрушение / стагнация / трансформация).

3. АНАЛИЗ ПРОСТРАНСТВА:
   Сравни Слой 1 (фасад) и Слой 4 (глубина).
   - Есть ли разрыв? (например, спокойствие снаружи и хаос внутри).

4. ЯДРО УБЕЖДЕНИЯ:
   - Дословно зафиксируй фразу из Слоя 5. Это формула внутреннего сценария.

РАСЧЕТ ШКАЛЫ ХОКИНСА:
- ГЛАВНОЕ ПРАВИЛО: Самый низкий обнаруженный маркер определяет итоговый уровень.
- ИНТЕЛЛЕКТУАЛИЗАЦИЯ (БАЙПАСИНГ): Если есть признаки умствования без телесного проживания — уровень НЕ может превышать 400 (Логика).
- ТРАНСФОРМАЦИЯ: Рост выше +150 за сессию возможен только при ярком физическом отклике и трансформации символа.

JSON:
{{
  "real_picture": "что происходит в подсознании (итог сравнения слоев 1 и 4)",
  "core_pattern": "название паттерна на основе Разлома",
  "reaction_pattern": "behavior type: action / avoidance / freeze",
  "body_signal": "основная телесная реакция, повторяющаяся в сессии",
  "shadow_active": "теневое качество резонанса",
  "key_choice": "анализ выбора на Разломе (тело + решение)",
  "recurring_symbol": "путь символа и его итог",
  "symbol_vector": "degraded / static / transformed",
  "core_belief": "дословное ядро из Слоя 5",
  "facade_vs_core": "описание разрыва между фасадом и глубиной",
  "mental_thinking": ["тип мышления 1", "тип мышления 2"],
  "mental_reactions": ["типичная телесная реакция 1", "типичная телесная реакция 2"],
  "mental_patterns": ["сценарный паттерн 1", "сценарный паттерн 2"],
  "mental_aspirations": ["скрытое стремление 1", "скрытое стремление 2"],
  "hawkins_score": 100,
  "hawkins_level": "уровень"
}}
"""
    }

    layer_prompt = layer_instructions.get(str(layer), "")
    
    if is_narrowing:
        layer_prompt += "\nВНИМАНИЕ: Предыдущий ответ пользователя был абстрактным. Используй СУЖАЮЩИЙ образ, чтобы добиться конкретики или телесного отклика.\n"

    return base_context, layer_prompt

async def run_avatar_layer(
    layer: str,
    archetype_id: int,
    sphere: str,
    previous_messages: list,
    scene_text: str = None,
    is_narrowing: bool = False,
    portrait_context: dict = None
) -> str:
    """
    Call OpenAI for a narrative layer, using the provided scene.
    """
    # 1. Build prompt with scene and portrait context
    system_prompt, layer_prompt = build_avatar_prompt(layer, archetype_id, sphere, {}, is_narrowing, scene_text, portrait_context)
    messages = [{"role": "system", "content": system_prompt}]
    
    if layer != "intro" and previous_messages:
        valid_history = []
        last_role = "system"
        
        for m in previous_messages:
            if not isinstance(m, dict): continue
            role = m.get("role", "user")
            content = str(m.get("content", ""))
            if not content.strip(): continue
            
            if role == last_role:
                if valid_history:
                    valid_history[-1]["content"] += "\n\n" + content
            else:
                valid_history.append({"role": role, "content": content})
                last_role = role
        
        
        messages.extend(valid_history)

    messages.append({"role": "system", "content": layer_prompt})

    try:
        model = settings.OPENAI_MODEL_FAST if layer != "mirror" else settings.OPENAI_MODEL
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=500,
        )
        return response.choices[0].message.content or "..."
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Sync OpenAI Error: {e}")
        return "Произошла ошибка при генерации ответа. Попробуйте нажать кнопку 'Далее' ещё раз."
