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


def build_sync_phase_prompt(
    phase: int,
    archetype_id: int,
    sphere: str,
    previous_phases: dict,
    phase_response: str = None,
) -> str:
    """Build the prompt for a specific synchronization phase."""
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})

    context = f"""
Ты — агент-нейрогид синхронизации AVATAR.
Цель: обойти логику и связаться с подсознанием, выявить скрытые истинные паттерны.
Архетип: {archetype.get('name', '')} ({archetype.get('shadow', '')} / {archetype.get('light', '')})
Сфера: {sphere_data.get('name_ru', sphere)} — {sphere_data.get('main_question', '')}

ВАЖНЕЙШИЙ КОНТЕКСТ:
Твоя задача — провести человека через исследование Тени и Света архетипа в этой сфере.
Метафоры и сцены должны строиться на пересечении ЭТОГО Архетипа и ЭТОЙ Сферы.

ПРАВИЛА:
1. КРАТКОСТЬ: Твой ответ должен быть до 400 символов. Без портянок. Меньше слов, больше плотности.
2. ФОРМАТ: Живой трансовый язык. Никаких списков, приветствий, воды.
3. ЗАПРЕТ: НИКОГДА не предлагай варианты выбора (А/Б/В/Г). Задавай только ОДИН открытый вопрос, бьющий в суть.
4. ФОКУС: Обращайся к чувствам, телу и метафорам, а не к логике. Не используй термины психологии.
"""

    phase_prompts = {
        1: f"""
ФАЗА 1 — ВРАТА (Настройка)
Создай темный, но притягательный образ (2-3 предложения). 
Отрази влияние Тени архетипа "{archetype.get('name', '')}" на сферу "{sphere_data.get('name_ru', sphere)}".
Никаких вопросов. Только описание атмосферы.
В конце — короткая фраза, приглашающая сделать шаг внутрь.
""",
        2: f"""
ФАЗА 2 — СТОЛКНОВЕНИЕ
Создай короткую острую сцену (2 предложения), где проявляется типичная проблема сферы "{sphere_data.get('name_ru', sphere)}".
Задай ОДИН вопрос: "Что первое вырывается наружу в этот момент: гнев, страх, желание сжаться или убежать?"
""",
        3: f"""
ФАЗА 3 — ЗЕРКАЛО ТЕНИ
Предыдущий ответ: {phase_response or 'не получен'}
Текущий багаж: {json.dumps(previous_phases, ensure_ascii=False)[:300]}

Опиши короткую реакцию Тени архетипа ({archetype.get('shadow', '')}) на ответ пользователя. Тень провоцирует.
Задай ОДИН вопрос: "Чего эта часть внутри вас боится больше всего?"
""",
        4: f"""
ФАЗА 4 — ОПУСКАНИЕ НА ДНО
Предыдущие данные: {json.dumps(previous_phases, ensure_ascii=False)[:300]}

Углуби предыдущий ответ. Метафорически опусти человека в самое дискомфортное состояние его Тени.
Спроси: "Если перестать бороться с этим чувством, какое одно слово его опишет?"
""",
        5: f"""
ФАЗА 5 — ТЕЛО
Данные предыдущих фаз: {json.dumps(previous_phases, ensure_ascii=False)[:400]}

Переведи фокус с мыслей на физические ощущения.
Спроси: "В какой части тела сейчас живет это напряжение или сопротивление? Как оно выглядит?"
""",
        6: f"""
ФАЗА 6 — ПРЕДЕЛ
Предыдущие данные: {json.dumps(previous_phases, ensure_ascii=False)[:400]}

Смоделируй точку кипения. Ситуация в сфере "{sphere_data.get('name_ru', sphere)}" достигает максимума, старые стратегии больше не работают.
Спроси: "Что вы готовы отпустить прямо сейчас, потому что нести это дальше невыносимо?"
""",
        7: f"""
ФАЗА 7 — ВМЕШАТЕЛЬСТВО СВЕТА
Данные: {json.dumps(previous_phases, ensure_ascii=False)[:500]}

Введи неожиданный элемент Света архетипа ({archetype.get('light', '')}). Свет не спасает, он дает ясность.
Спроси: "Если бы вы посмотрели на ситуацию глазами этой силы, что меняется?"
""",
        8: f"""
ФАЗА 8 — НОВЫЙ ВЫБОР
Данные сессии: {json.dumps(previous_phases, ensure_ascii=False)[:500]}

Реальность начинает меняться. Укажи на крошечный, но реальный первый шаг по-новому.
Спроси: "Какое крошечное действие по-другому вы можете сделать уже сегодня?"
""",
        9: f"""
ФАЗА 9 — КРИСТАЛЛИЗАЦИЯ
Все данные: {json.dumps(previous_phases, ensure_ascii=False)[:800]}

Опираясь на инсайты сессии, сформулируй 1 коренное ограничивающее убеждение, которое мы обнаружили, и 1 освобождающее.
Спроси: "Вам откликается этот сдвиг?"
""",
        10: f"""
ФАЗА 10 — ИНТЕГРАЦИЯ
Все данные: {json.dumps(previous_phases, ensure_ascii=False)[:800]}

Мягкое завершение. Подсвети, что энергия, которая уходила на борьбу с Тенью, теперь свободна.
Задай финальный вопрос: "Как ощущается пространство внутри вас сейчас?"
""",
    }

    return context + phase_prompts.get(phase, "Продолжи сессию.")


async def sync_phase_response(
    phase: int,
    archetype_id: int,
    sphere: str,
    previous_phases: dict,
    user_message: str = None,
    token_budget: int = 1200,
) -> str:
    """Generate AI response for a synchronization phase."""
    prompt = build_sync_phase_prompt(phase, archetype_id, sphere, previous_phases, user_message)

    messages = [{"role": "system", "content": prompt}]
    if user_message and phase > 1:
        messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=token_budget,
        temperature=0.85,
    )
    return response.choices[0].message.content


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
