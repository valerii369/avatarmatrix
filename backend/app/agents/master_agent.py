"""
Master Agent: orchestrates all AI interactions.
Routes requests to appropriate sphere agent + Hawkins level agent.
"""
import json
import os
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "archetypes.json")) as f:
    ARCHETYPES = {item["id"]: item for item in json.load(f)}

with open(os.path.join(DATA_DIR, "spheres.json")) as f:
    SPHERES = {item["key"]: item for item in json.load(f)}

try:
    with open(os.path.join(DATA_DIR, "archetype_sphere_matrix.json"), "r", encoding="utf-8") as f:
        MATRIX_DATA = json.load(f)
except Exception:
    MATRIX_DATA = {}

with open(os.path.join(DATA_DIR, "hawkins_scale.json")) as f:
    HAWKINS_SCALE = json.load(f)

SPHERE_AGENT_STYLES = {
    "IDENTITY": "зеркало",
    "MONEY": "практичный мудрец",
    "RELATIONS": "тёплый честный друг",
    "FAMILY": "мудрый старейшина",
    "MISSION": "вдохновляющий стратег",
    "HEALTH": "мудрый целитель",
    "SOCIETY": "стратег-наставник",
    "SPIRIT": "проводник тишины",
}

LEVEL_METHODOLOGIES = {
    1: {"range": "20-75",  "style": "максимально мягкий, безоценочный, тёплый", "focus": "Я имею право существовать → Я достоин быть", "avoid": "конфронтацию, глубокий анализ, вопросы 'почему'"},
    2: {"range": "75-125", "style": "поддерживающий, как мудрый друг", "focus": "Мир опасен → Я могу справиться", "avoid": "просто перестань бояться, рационализацию"},
    3: {"range": "125-175","style": "уважительный, прямой, не боится конфронтации", "focus": "Они виноваты → Я беру ответственность", "avoid": "подавление гнева, морализаторство"},
    4: {"range": "175-250","style": "партнёрский, поддерживающий рост", "focus": "Может быть → Я выбираю", "avoid": "спасательство, излишнюю мягкость"},
    5: {"range": "250-350","style": "наставник, ментор", "focus": "Я справляюсь → Я расту через это", "avoid": "повторение базовых вещей"},
    6: {"range": "350-400","style": "мудрый, глубокий, с юмором", "focus": "Я понимаю → Я чувствую и понимаю", "avoid": "ещё больше анализа, интеллектуализацию"},
    7: {"range": "400-500","style": "со-путник, равный", "focus": "Я люблю когда... → Я люблю", "avoid": "учительский тон, наставничество"},
    8: {"range": "500-540","style": "минимальный — человек сам ведёт", "focus": "Как нести это в мир?", "avoid": ""},
    9: {"range": "540-700","style": "минимальный, пространство тишины", "focus": "поддержание и углубление", "avoid": ""},
    10: {"range": "700+", "style": "зеркало, пространство", "focus": "фиксация состояния", "avoid": ""},
}


def get_hawkins_agent_level(hawkins_score: int) -> int:
    """Determine which level agent to use based on Hawkins score."""
    if hawkins_score < 75:   return 1
    if hawkins_score < 125:  return 2
    if hawkins_score < 175:  return 3
    if hawkins_score < 250:  return 4
    if hawkins_score < 350:  return 5
    if hawkins_score < 400:  return 6
    if hawkins_score < 500:  return 7
    if hawkins_score < 540:  return 8
    if hawkins_score < 700:  return 9
    return 10


def is_abstract_response(text: str) -> bool:
    """
    Check if user response is too abstract based on keywords and lack of body part mentions.
    """
    if not text:
        return True
    
    text_lower = text.lower()
    
    # Body parts keywords (Russian)
    body_parts = ["грудь", "живот", "горло", "рук", "ног", "спин", "плеч", "голов", "солнечн", "дыхани", "сердц", "тело", "мышц"]
    has_body = any(bp in text_lower for bp in body_parts)
    
    # Abstract keywords
    abstract_keywords = ["мир", "творить", "помогать", "всё", "развитие", "рост", "гармония", "счастье", "любовь"]
    is_vague = any(ak == text_lower.strip() or f" {ak} " in f" {text_lower} " for ak in abstract_keywords)
    
    # If no body mention and contains abstract keywords OR it's just too short/generic
    if not has_body and (is_vague or len(text.split()) < 3):
        return True
        
    return False


def build_avatar_prompt(
    layer: str,
    archetype_id: int,
    sphere: str,
    session_data: dict,
    is_narrowing: bool = False
) -> str:
    """Build the prompt for a specific narrative layer (1, 2, 3) or Mirror analysis."""
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})
    
    matrix = MATRIX_DATA.get(str(archetype_id), {}).get(sphere, {})
    arch_shadow = matrix.get("shadow", archetype.get('shadow', ''))
    arch_light = matrix.get("light", archetype.get('light', ''))

    base_context = f"""
Ты — агент синхронизации AVATAR.
Метод: нарративная проекция. Ты даешь образы-сцены, человек их достраивает.
Цель: ЧИСТАЯ ДИАГНОСТИКА. Достать из подсознания реальную картину того, что происходит сейчас.
Никакой трансформации или коррекции на этом этапе.

Архетип: {archetype.get('name', '')} ({arch_shadow} / {arch_light})
Сфера: {sphere_data.get('name_ru', sphere)} — {sphere_data.get('main_question', '')}

ПРАВИЛА:
1. КРАТКОСТЬ: Мах 400 символов.
2. ЖИВОЙ ЯЗЫК: Никаких списков, приветствий, психологических терминов.
3. ОДИН ВОПРОС: Всегда заканчивай ОДНИМ открытым вопросом, бьющим в суть.
4. НЕТ ВАРИАНТАМ: Не предлагай выбор (А/Б/В).
"""

    layer_instructions = {
        "intro": """
ВСТУПЛЕНИЕ (БЕЗ ВОПРОСА)
Цель: рассказать человеку, что сейчас будет происходить.
Объясни кратко:
1. Это диагностическая сессия из 3-х слоев: Поверхность, Под поверхностью, Дно.
2. Метод — нарративная проекция (я даю образы, ты их достраиваешь).
3. Важно отвечать конкретно, обращая внимание на чувства и тело.
Закончи приглашением войти внутрь (например, "Готов войти?"). НЕ ЗАДАВАЙ НИКАКИХ ДРУГИХ ВОПРОСОВ. ВООБЩЕ НИКАКИХ ВОПРОСОВ, КРОМЕ ПРИГЛАШЕНИЯ.
""",
        "1": """
СЛОЙ 1 — ПОВЕРХНОСТЬ
Цель: зафиксировать то, что человек ДУМАЕТ о своей ситуации.
Создай 1-2 образа, отражающих типичную социальную или внешнюю сторону этой сферы.
Задай вопрос, помогающий человеку описать его текущую декларативную картину.
""",
        "2": """
СЛОЙ 2 — ПОД ПОВЕРХНОСТЬЮ
Цель: обойти логику, достать реальные драйверы.
Создай образы, создающие лёгкое давление (не комфортное, но не травматичное).
Заставь человека заглянуть за его привычные объяснения.
""",
        "3": """
СЛОЙ 3 — ДНО
Цель: корневой паттерн + телесный якорь.
Создай один мощный образ — исчезновение всего привычного ресурса в этой ситуации.
Требуй фиксации: ГДЕ в теле, КАК выглядит, ОДНО слово-описание.
""",
        "mirror": f"""
ФИНАЛ — ЗЕРКАЛО (АНАЛИЗ)
Твоя задача — проанализировать ВСЮ сессию целиком и сформулировать реальную картину.
Не интерпретируй, а отражай. Что на самом деле происходит?
Какой паттерн управляет? Что из Тени активно? Где это живет в теле?

Обязательно определи НАЙНИЗШУЮ точку по шкале Хокинса во всей сессии.

Отвечай СТРОГО в JSON формате:
{{
  "real_picture": "...",
  "core_pattern": "...",
  "shadow_active": "...",
  "body_anchor": "...",
  "first_insight": "...",
  "hawkins_score": 100,
  "hawkins_level": "Страх"
}}
"""
    }

    prompt = base_context + layer_instructions.get(str(layer), "")
    
    if is_narrowing:
        prompt += "\nВНИМАНИЕ: Предыдущий ответ пользователя был абстрактным. Используй СУЖАЮЩИЙ образ, чтобы добиться конкретики или телесного отклика.\n"

    return prompt


async def run_avatar_layer(
    layer: str,
    archetype_id: int,
    sphere: str,
    previous_messages: list,
    is_narrowing: bool = False
) -> str:
    """Call OpenAI for a narrative layer."""
    prompt = build_avatar_prompt(layer, archetype_id, sphere, {}, is_narrowing)
    
    messages = [{"role": "system", "content": prompt}]
    # For layers, we need history. 
    # CRITICAL: OpenAI requires alternating roles: assistant -> user -> assistant...
    # Since we use a SYSTEM prompt for instructions, the first message in 'messages' 
    # after system usually should be 'user' OR we must ensure alternation.
    if layer != "intro":
        if previous_messages:
            # Filter and ensure alternation/validity
            valid_history = []
            for m in previous_messages:
                if isinstance(m, dict) and m.get("content") is not None:
                    valid_history.append({
                        "role": m.get("role", "user"),
                        "content": str(m["content"])
                    })
            messages.extend(valid_history)

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=400 if layer == "intro" else 300,
        temperature=0.85 if layer != "mirror" else 0.2,
    )
    return response.choices[0].message.content


async def run_mirror_analysis(
    archetype_id: int,
    sphere: str,
    session_transcript: list
) -> dict:
    """Run the final analytical 'Mirror' call."""
    prompt = build_avatar_prompt("mirror", archetype_id, sphere, {})
    
    messages = [{"role": "system", "content": prompt}]
    # Format transcript for the analyst
    transcript_text = "\n".join([f"{m['role']}: {m['content']}" for m in session_transcript])
    messages.append({"role": "user", "content": f"Транскрипт сессии:\n{transcript_text}"})

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=600,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "real_picture": "Ошибка анализа",
            "core_pattern": "Не определен",
            "shadow_active": "Не определен",
            "body_anchor": "Не определен",
            "first_insight": "Не определен",
            "hawkins_score": 100,
            "hawkins_level": "Страх"
        }


async def alignment_session_message(
    stage: int,
    archetype_id: int,
    sphere: str,
    hawkins_score: int,
    chat_history: list[dict],
    user_message: str,
    core_belief: str = "",
    shadow_pattern: str = "",
    token_budget: int = 2000,
) -> str:
    """Generate AI response for an alignment session stage."""
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})
    agent_level = get_hawkins_agent_level(hawkins_score)
    methodology = LEVEL_METHODOLOGIES.get(agent_level, LEVEL_METHODOLOGIES[1])
    sphere_style = SPHERE_AGENT_STYLES.get(sphere, "мудрый проводник")

    stages = {
        1: "КОНТАКТ С ПАТТЕРНОМ: Вернись к исходному паттерну. Активируй эмоциональный заряд через текстовую визуализацию ситуации. Спроси какую эмоцию вызывает это прямо сейчас.",
        2: "ОСОЗНАНИЕ: Подсвети механизм как паттерн работает, что защищает, какую функцию выполняет. 'Заметьте что происходит когда вы [реакция]...' Цель: человек ВИДИТ свой автоматизм.",
        3: "ПЕРЕЖИВАНИЕ: Проведи через эмоцию не избегая её. Текстовая визуализация — человек проживает ситуацию с новым углом зрения. Цель: эмоциональная разрядка.",
        4: "ПЕРЕЗАПИСЬ: Та же ситуация — новая реакция. 'А если в этой ситуации вы бы [новая реакция]?' Текстовая визуализация альтернативы. Цель: создать новый нейронный путь.",
        5: "ЗАКРЕПЛЕНИЕ: Помоги сформулировать новое убеждение. Проживание ресурсного состояния. 'Как это ощущается в теле?' Цель: якорение нового состояния.",
        6: "МОСТ В РЕАЛЬНОСТЬ: 'В какой конкретной ситуации на этой неделе вы можете применить это?' Конкретный план. Сформулируй 1-2 действия для интеграции.",
    }

    system_prompt = f"""Ты — агент выравнивания в системе AVATAR. Стиль ведения: {sphere_style}.

Архетип: {archetype.get('name', '')} | Сфера: {sphere_data.get('name_ru', sphere)}
Уровень Хокинса: {hawkins_score} | Ведёшь по методологии уровня {agent_level} ({methodology['range']})

Стиль: {methodology['style']}
Фокус перезаписи: {methodology['focus']}
ИЗБЕГАЙ: {methodology['avoid']}

Ядро-убеждение пользователя: {core_belief or 'не определено'}
Паттерн тени: {shadow_pattern or 'не определён'}

ТЕКУЩИЙ ЭТАП {stage}/6: {stages.get(stage, '')}

ПРАВИЛА:
- Короткие ответы (3-6 предложений) если не нужен длинный текст
- Один вопрос в конце (не несколько)
- Живой язык, без психологических терминов
- Полное присутствие в процессе
- НЕ торопи к следующему этапу пока текущий не завершён"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-20:])  # Last 20 messages for context
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=token_budget,
        temperature=0.8,
    )
    return response.choices[0].message.content


async def evaluate_hawkins(user_text: str, context: str = "") -> dict:
    """
    Evaluate Hawkins score from user's text.
    Returns {score, level, dominant_emotion, confidence}
    """
    prompt = f"""Ты — агент оценки уровня сознания по шкале Хокинса.

Контекст сессии: {context[:500] if context else 'не задан'}

Текст пользователя: "{user_text}"

Определи:
1. Доминирующую эмоцию
2. Балл Хокинса (от 20 до 1000)
3. Уровень (Стыд/Вина/Апатия/Горе/Страх/Желание/Гнев/Гордыня/Смелость/Нейтральность/Готовность/Принятие/Разум/Любовь/Радость/Мир/Просветление)
4. Уверенность (1-10)

Отвечай строго в JSON:
{{"score": 125, "level": "Желание", "dominant_emotion": "жажда/ненасытность", "confidence": 7}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_FAST,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"score": 100, "level": "Страх", "dominant_emotion": "тревога", "confidence": 3}


async def extract_sync_insights(phase_data: dict, archetype_id: int, sphere: str) -> dict:
    """
    Extract structured insights from completed sync session.
    Returns core_belief, shadow_pattern, body_anchor, tags, etc.
    """
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})

    prompt = f"""Ты — аналитик сессии глубокой синхронизации AVATAR.
Оцениваешь результаты погружения в подсознание.

Архетип: {archetype.get('name', '')} | Сфера: {sphere_data.get('name_ru', sphere)}

Транскрипт всех 10 фаз:
{json.dumps(phase_data, ensure_ascii=False, indent=2)[:2000]}

ЗАДАЧА 1: Структурировать инсайты (ядро-убеждение, паттерн тени, якорь в теле, страхи, защита).
ЗАДАЧА 2: Проанализировать ВСЕ ответы пользователя и определить НАЙНИЗШУЮ проявленную точку по шкале Хокинса.
Ищи не то, что человек социально декларирует, а то, что сквозит в ответах: страх (100), гнев (150), апатия (50), вина (30) и т.д.

Отвечай строго в JSON формата:
{{
  "core_belief": "я не достоин финансового успеха",
  "shadow_pattern": "избегание + замирание",
  "body_anchor": "сжатие в груди",
  "projection": "зависть к успешным",
  "avoidance": "выбор безопасного пути",
  "dominant_emotion": "страх/тревога",
  "tags": ["недостойность", "избегание", "страх_успеха", "контроль"],
  "hawkins_score": 100,
  "hawkins_level": "Страх"
}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "core_belief": "", "shadow_pattern": "", "body_anchor": "",
            "projection": "", "avoidance": "", "dominant_emotion": "",
            "tags": [], "hawkins_score": 100, "hawkins_level": "Страх"
        }
