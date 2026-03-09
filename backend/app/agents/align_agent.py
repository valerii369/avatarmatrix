from .common import (
    client, settings, ARCHETYPES, SPHERES, MATRIX_DATA,
    SPHERE_AGENT_STYLES, LEVEL_METHODOLOGIES, LEVEL_GOALS
)
from .hawkins_agent import get_hawkins_agent_level

async def alignment_session_message(
    stage: int,
    archetype_id: int,
    sphere: str,
    hawkins_score: int,
    chat_history: list[dict],
    user_message: str,
    core_belief: str = "",
    shadow_pattern: str = "",
    history_context: str = "",
    token_budget: int = 2000,
    is_deepening: bool = False
) -> str:
    """Generate AI response for an alignment session stage using Quantum Logic."""
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})
    agent_level = get_hawkins_agent_level(hawkins_score)
    methodology = LEVEL_METHODOLOGIES.get(agent_level, LEVEL_METHODOLOGIES.get(1))
    sphere_style = SPHERE_AGENT_STYLES.get(sphere, "мудрый проводник")
    
    # Identify overarching goal based on Hawkins range
    goal_key = "SURVIVAL"
    if 200 <= hawkins_score < 500: goal_key = "GROWTH"
    elif hawkins_score >= 500: goal_key = "PRESENCE"
    current_goal = LEVEL_GOALS[goal_key]["goal"]

    # Sphere specific data
    techniques = ", ".join(sphere_data.get("techniques", []))
    patterns = ", ".join(sphere_data.get("patterns", []))
    
    # Archetype components from Matrix (Sphere-Specific)
    matrix = MATRIX_DATA.get(str(archetype_id), {}).get(sphere, {})
    
    # Prioritize Matrix data, fallback to general Archetype data
    arch_name = archetype.get('name', 'Архетип')
    arch_light = matrix.get("light", archetype.get('light', ''))
    arch_description = matrix.get("description", archetype.get('description', ''))
    arch_shadow = matrix.get("shadow", archetype.get('shadow', ''))
    
    # For reference
    arch_base_shadow = archetype.get('shadow', '')
    arch_base_light = archetype.get('light', '')

    protocols = {
        1: f"ПРОТОКОЛ 1: РЕГУЛЯЦИЯ (СОМАТИКА И ТЕНЬ). Задача: обнаружить напряжение в теле, связанное с паттерном, и осознать его защитную функцию (вторичную выгоду). Теневой аспект: {arch_shadow}. Техники сферы: {techniques}.",
        2: f"ПРОТОКОЛ 2: ИНТЕГРАЦИЯ РЕСУРСА (СВЕТ). Задача: впустить Свет Архетипа ({arch_name}: {arch_light}) в место напряжения. Прожить новое состояние расширения и тепла в теле через 'Архетипическое Дыхание'.",
        3: f"ПРОТОКОЛ 3: ОБНОВЛЕНИЕ СЦЕНАРИЯ (ДЕЙСТВИЕ). Задача: сформировать новую поведенческую формулу (Код Силы). Представить конкретную ситуацию из жизни, где ты действуешь по-новому. Итог: ОДНО МИКРО-ДЕЙСТВИЕ на неделю.",
    }

    deepening_prompt = ""
    if is_deepening:
        deepening_prompt = "\nВНИМАНИЕ: Ответ пользователя был поверхностным. НЕ переходи к следующему протоколу. Углуби текущий процесс, требуй больше соматических (телесных) деталей.\n"

    system_prompt = f""" Ты — агент ВЫРАВНИВАНИЯ системы AVATAR. Стиль: {sphere_style}.
Архетип: {arch_name} | Сфера: {sphere_data.get('name_ru', sphere)}
Уровень Хокинса: {hawkins_score} | Методология: {methodology['style']}

ГЛОБАЛЬНАЯ ЦЕЛЬ: {current_goal}

ИНСТРУКЦИЯ (СТРОГО):
- Ты ведешь пользователя через 3 протокола развития.
- ТЕКУЩИЙ ПРОТОКОЛ {stage}/3: {protocols.get(stage, protocols[1])}
{deepening_prompt}

ПРАВИЛА МАСТЕРСТВА:
1. СОМАТИЧЕСКИЙ ЯКОРЬ: В каждом ответе возвращай внимание пользователя к ощущениям в теле.
2. БЕЗ ПСИХОАНАЛИЗА: Не объясняй 'почему', помогай 'прожить'.
3. СВЕТ И ТЕНЬ: Используй данные матрицы для этой сферы: Тень — {arch_shadow}, Свет — {arch_light}.
4. КОРОТКО: Ответ 2-4 предложения. 
5. ОДИН ВОПРОС: Всегда заканчивай одним открытым вопросом.
6. ФИНАЛ: В 3-м протоколе обязательно доведи до конкретного микро-действия в реальности.
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-15:])
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_FAST,
        messages=messages,
        max_tokens=token_budget,
        temperature=0.7,
    )
    
    return response.choices[0].message.content or "..."

async def check_alignment_depth(text: str) -> dict:
    """
    Evaluate the depth of a user's response to decide on stage transition.
    Returns: {"is_sufficient": bool, "reason": str}
    """
    if not text:
        return {"is_sufficient": False, "reason": "empty"}
    
    text_lower = text.lower()
    words = text.split()
    
    # Body parts keywords (Russian)
    body_parts = ["грудь", "живот", "горло", "рук", "ног", "спин", "плеч", "голов", "солнечн", "дыхани", "сердц", "тело", "мышц", "колен", "таз"]
    has_body = any(bp in text_lower for bp in body_parts)
    
    # Emotional keywords (Russian) - broadly negative for shift logic
    emotions = ["страх", "боль", "гнев", "стыд", "вино", "тяжесть", "ком", "сжати", "пустота", "холод", "жар", "дрожь"]
    has_emotion = any(e in text_lower for e in emotions)

    # Criteria for sufficiency:
    # 1. At least 5 words long
    # 2. Mentions body parts OR deep emotions
    
    is_sufficient = len(words) >= 5 and (has_body or has_emotion)
    
    return {
        "is_sufficient": is_sufficient,
        "reason": "depth_check_passed" if is_sufficient else "too_abstract_or_short"
    }
