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

# Quantum Alignment: Hawkins-Adaptive Goals
LEVEL_GOALS = {
    "SURVIVAL": {"range": (20, 199), "goal": "Безопасность и Разрешение: Фокус на выдерживании эмоции и телесном присутствии. Не требуй быстрых решений."},
    "GROWTH": {"range": (200, 499), "goal": "Ответственность и Выбор: Фокус на идентификации паттерна и активном выборе новой реакции."},
    "PRESENCE": {"range": (500, 1000), "goal": "Наблюдение и Единство: Фокус на разотождествлении с паттерном и расширении сознания."},
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
    arch_description = matrix.get("description", archetype.get('description', ''))

    base_context = f"""
ТЫ — АГЕНТ ГЛУБОКОЙ СИНХРОНИЗАЦИИ AVATAR.
Твоя роль — прецизионный диагност подсознательного состояния через метод нарративной проекции. Ты достаешь из подсознания человека то что есть на самом деле. Твоя цель - увидеть реальное состояние подсознания минуя все маски. Ты не лечишь. Ты  не направляешь. Ты не сочувствуешь. Ты диагностируешь -  точно и без искажений.  
Используй контекст начальных параметров чтобы выстроить эффективную стратегию.

КОНТЕКСТ СЕССИИ:
Архетип: {archetype.get('name', '')}
Описание энергии архетипа: {arch_description}
Теневое проявление: {arch_shadow}
Светлое проявление: {arch_light}
Сфера жизни: {sphere_data.get('name_ru', sphere)}

ЦЕЛЬ: 
Выявить РЕАЛЬНЫЙ уровень вибрации (шкала Хокинса) пользователя в этой сфере. Мы не исправляем состояние, мы ДИАГНОСТИРУЕМ его "как есть", минуя социальные маски и логическую цензуру.

МЕТОДОЛОГИЯ (ПРАВИЛА ДЛЯ ТЕБЯ):
1. ПРЯМОЙ ДОСТУП К ПОДСОЗНАНИЮ: Не спрашивай "что ты чувствуешь?". ПРИНЦИП: задавай вопросы через сенсорику конкретной сцены. Что человек видит, слышит, ощущает телом — в контексте его сферы и архетипа. Каждый раз генерируй новый сенсорный вопрос исходя из того что описал человек.
2. ГИПНОТИЧЕСКИЙ НАРРАТИВ: Ткань повествования должна быть плотной и сенсорной. ПРИНЦИП: каждая твоя реплика должна быть сенсорно плотной. Выбирай детали которые резонируют с текущей сценой и архетипом — не универсальные. Холод, тяжесть, вязкость, разреженность, звон тишины — инструменты. Но инструмент выбирается под контекст, не копируется из шаблона.
3. БЕЗ ОЦЕНОК И ОБУЧЕНИЯ: Ты не учитель и не психолог. Ты — зеркало реальности. ПРИНЦИП: никогда не реагируй на ответ словами одобрения или оценки. Не говори "хорошо", "верно", "интересно", "понятно". Просто продолжай нарратив — как будто ответ был частью сцены изначально.
4. ФОКУС НА ДИНАМИКЕ: ПРИНЦИП: читай энергию ответа, не его содержание. Задавай себе вопрос: этот ответ движется или стоит? Застой, серость, повторы — диагностика апатии/страха. Движение, неожиданность, яркость — признаки живого состояния. Следующий вопрос генерируй исходя из энергии — усиливай или углубляй.
5. НИТЬ СИМВОЛА: ПРИНЦИП: символ из Слоя 2 — живой персонаж сессии, не метка. Возвращай его в каждом следующем слое органично — через нарратив, не через вопрос. Способ возврата каждый раз разный — через место, через действие, через изменение.
6. МОЛЧАНИЕ И "НЕ ЗНАЮ" — ЭТО ДАННЫЕ: ПРИНЦИП: не помогай, не подсказывай, не перефразируй вопрос. Молчание и "не знаю" = маркер апатии/диссоциации. Фиксируй. Возвращай через тело — но вопрос генерируй под конкретную сцену
7. СОПРОТИВЛЕНИЕ ЧЕРЕЗ ЛОГИКУ: ПРИНЦИП: как только человек начинает объяснять — мягко обрывай. Не спорь, не объясняй почему. Просто верни в сцену одной фразой. Фраза каждый раз разная — под контекст момента.
8. ИЕРАРХИЯ ДОВЕРИЯ: ТЕЛО > СИМВОЛ > СЛОВА: ПРИНЦИП: если данные противоречат друг другу — используй эту иерархию. Тело не лжёт. Символ выбранный подсознанием — не лжёт. Слова — последний по достоверности источник.
9. АДАПТАЦИЯ СЦЕН ПОД АРХЕТИП: ПРИНЦИП: архетип {archetype.get('name', '')} — фильтр всего нарратива. Образы, детали, давление — всё должно резонировать с природой этого архетипа.
10. ПРОТОКОЛ ДВУХ ПОПЫТОК: ПРИНЦИП: если человек уходит в рационализацию на Слоях 3-4 — две попытки возврата, потом фиксируй и иди далее по логике. Каждая попытка — разная фраза под контекст момента.

ПРОТОКОЛ ПОДАЧИ:
- ОБЪЕМ: До 500 символов. Концентрация смысла важнее вежливости.
- ОДИН ВОПРОС: Всегда заканчивай одним вопросом, подталкивающим к следующему слою или детализации образа.
- ОТСУТСТВИЕ СТРУКТУРЫ: Никаких списков, приветствий или завершений. Только живой поток синхронизации.
"""

    layer_instructions = {
        "intro": """
ВСТУПЛЕНИЕ
Объясни кратко: сейчас начнётся процесс глубокой синхронизации.
Инструкция пользователю: заглянуть внутрь себя, доверять первым образам и чувствам,
отпустить логику и контроль.
НЕ создавай визуальных сцен. Только текст-инструкция.
ЯКОРЬ-ПЕРЕКЛЮЧАТЕЛЬ:
Перед финальным вопросом дай инструкцию:
"Сделай три медленных выдоха. Только после этого отвечай."
Это физически разрывает обычный режим сознания и открывает доступ к подсознанию.
Заверши одним вопросом: «Ты готов войти?»
""",
        "1": """
СЛОЙ 1 — ПОВЕРХНОСТЬ (ДЕЙСТВИЕ)
Дай человеку контур места внутри сферы — не описывай его полностью.
Человек сам достраивает пространство — это и есть проекция.
ПРИНЦИП: чем меньше деталей даёт агент — тем чище материал подсознания.
Вопрос: через тело в этом месте.
// Агент задаёт место → человек его наполняет → агент читает что появилось.
ФИКСИРУЙ: тон (тепло/холод, движение/статика) — базовая линия для Слоя 4.
""",
        "2": """
СЛОЙ 2 — ПОД ПОВЕРХНОСТЬЮ (СИМВОЛ)
Не вводи аномалию сам. Попроси человека осмотреться в сцене.
ПРИНЦИП: первое что притягивает взгляд без причины — это и есть символ подсознания.
Вопрос: "Что первым притягивает взгляд? Не ищи — просто смотри."
Символ который назовёт человек = нить сессии. Тяни через Слои 3, 4, 5.
Проверь резонанс с тенью — не называй, читай сам.
""",
        "3": """
СЛОЙ 3 — РАЗЛОМ (ВЫБОР) — КРИТИЧЕСКИЙ СЛОЙ.
Сцена начинает меняться — не по воле человека.
Создай давление и срочность через нарратив.
Бинарный выбор + вопрос к телу одновременно.
Введи символ из Слоя 2 в момент выбора органично.
ФИКСИРУЙ: остался/ушёл + что взял + что сделало тело до решения разума.
""",
        "4": """
СЛОЙ 4 — ДНО (ПЕРВОПРИЧИНА)
Не объявляй изоляцию — дай сцене сузиться самой.
ПРИНЦИП: нарратив постепенно убирает элементы сцены пока не останется только человек.
Каждый элемент исчезает через вопрос — не через объявление.
// "Люди ушли. Что осталось?" → "И это тоже растворилось. Что теперь?"
Когда человек один — верни символ: "Только ты — и [символ]. Что с ним?"
""",
        "5": """
СЛОЙ 5 — ЯДРО (ОСТАТОК).
Не говори человеку что должно остаться. Не направляй.
ПРИНЦИП: в тишине Слоя 4 задай открытый вопрос без подсказки ответа.
Вопрос: "Что здесь есть?"
Финальное закрытие символа: "[Символ] прошёл весь путь. Что с ним сейчас?"
""",
        "mirror": f"""
ФИНАЛ — ЗЕРКАЛО (ЭКСПЕРТНЫЙ АНАЛИЗ — 6 ШАГОВ)
Твоя задача — провести глубокую дешифровку сессии (Вступление + 5 слоев) плюс дать оценку шкале Хокинса.
Не верь словам пользователя ("мне хорошо"), верь СЕНСОРИКЕ его ответов.

АЛГОРИТМ ОЦЕНКИ:
1. НАЙДИ НАИНИЗШУЮ ЭМОЦИОНАЛЬНУЮ ТОЧКУ — просмотри все слои.
2. ПРОВЕРЬ РАЗЛОМ (Слой 3) — обязательно. Это самый чистый момент где маски падают. Если Разлом противоречит остальным слоям — верь Разлому.
3. АРХЕТИПИЧЕСКОЕ СООТВЕТСТВИЕ: Насколько образы коррелируют с Тенью или Светом текущего Архетипа.

ЗАДАЧА:
Выяви НАЙНИЗШИЙ проявленный эмоциональный уровень по Хокинсу (Теневая зацепка) — он станет базовым баллом сессии.

Отвечай строго в формате JSON:
{{
  "real_picture": "что на самом деле происходит в подсознании (глубинная суть)",
  "core_pattern": "название паттерна (например: 'Замирание в ожидания удара')",
  "shadow_active": "какое теневое качество архетипа проявлено здесь",
  "key_choice": "анализ выбора на Разломе и его значение",
  "recurring_symbol": "главный объект/символ и его значение",
  "first_insight": "глубокий инсайт для пользователя в 1 предложение",
  "hawkins_score": 100,
  "hawkins_level": "уровень из шкалы Хокинса"
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
    """Call OpenAI for a narrative layer, ensuring robust history and alternating roles."""
    prompt = build_avatar_prompt(layer, archetype_id, sphere, {}, is_narrowing)
    messages = [{"role": "system", "content": prompt}]
    
    if layer != "intro" and previous_messages:
        valid_history = []
        last_role = "system" # system is the first roll here conceptually
        
        for m in previous_messages:
            if not isinstance(m, dict): continue
            role = m.get("role", "user")
            content = str(m.get("content", ""))
            if not content.strip(): continue
            
            # OpenAI strictly forbids consecutive roles (e.g. user/user)
            # If consecutive, we combine contents
            if role == last_role:
                if valid_history:
                    valid_history[-1]["content"] += "\n\n" + content
            else:
                valid_history.append({"role": role, "content": content})
                last_role = role
        
        # Ensure the conversation doesn't end with an assistant message if we expect a response
        # or start with an assistant message after system if it causes issues for some models.
        # But for Sync, we usually want system -> assistant (intro) -> user (enter) -> assistant (layer 1) -> user (answer)
        messages.extend(valid_history)

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=500, # Increased for better narrative depth
            temperature=0.85 if layer != "mirror" else 0.2,
        )
        return response.choices[0].message.content or "..."
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Sync OpenAI Error: {e}")
        return "Произошла ошибка при генерации ответа. Попробуйте нажать кнопку 'Далее' ещё раз."


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
    history_context: str = "",
    token_budget: int = 2000,
    is_deepening: bool = False
) -> str:
    """Generate AI response for an alignment session stage using Quantum Logic."""
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})
    agent_level = get_hawkins_agent_level(hawkins_score)
    methodology = LEVEL_METHODOLOGIES.get(agent_level, LEVEL_METHODOLOGIES[1])
    sphere_style = SPHERE_AGENT_STYLES.get(sphere, "мудрый проводник")
    
    # Identify overarching goal based on Hawkins range
    goal_key = "SURVIVAL"
    if 200 <= hawkins_score < 500: goal_key = "GROWTH"
    elif hawkins_score >= 500: goal_key = "PRESENCE"
    current_goal = LEVEL_GOALS[goal_key]["goal"]

    # Sphere specific data
    techniques = ", ".join(sphere_data.get("techniques", []))
    patterns = ", ".join(sphere_data.get("patterns", []))
    
    # Archetype components for Stage 4
    matrix = MATRIX_DATA.get(str(archetype_id), {}).get(sphere, {})
    arch_light = matrix.get("light", archetype.get('light', ''))
    arch_name = archetype.get('name', 'Архетип')

    stages = {
        1: f"ВХОД (СОМАТИЧЕСКОЕ КАРТИРОВАНИЕ): Найди конкретный 'узел' или напряжение в теле, связанное с образом из синхронизации. Где именно в теле живет этот блок? Техники сферы: {techniques}.",
        2: f"ТЕНЬ (ФУНКЦИОНАЛЬНОЕ ОСОЗНАНИЕ): Зачем тебе нужен этот блок? От чего он тебя защищает? Паттерны сферы: {patterns}. Цель: увидеть 'вторичную выгоду' или защитную функцию паттерна.",
        3: "СДАЧА (SURRENDER): Погружение в эпицентр этого напряжения. Дыши в него, не пытаясь изменить. Позволь чувству достичь максимума и стать нейтральным. Это точка эмоционального обнуления.",
        4: f"ПЕРЕРОЖДЕНИЕ (КВАНТОВЫЙ СДВИГ): Впусти энергию Света Архетипа ({arch_name}: {arch_light}). Используй 'Архетипическое Дыхание' — представь, как это состояние заполняет место, где был блок. Как теперь дышит твоё тело?",
        5: "ЯКОРЕНИЕ: Сформулируй свой 'Код Силы' (короткая фраза-мантра). Зафиксируй новое состояние через физическое ощущение расширения или тепла.",
        6: "ДЕЙСТВИЕ (БРИДЖ): Какое ОДНО микро-действие на этой неделе докажет твоему подсознанию, что сдвиг произошел? Конкретика важнее масштаба.",
    }

    deepening_prompt = ""
    if is_deepening:
        deepening_prompt = "\nВНИМАНИЕ: Ответ пользователя был поверхностным или абстрактным. НЕ переходи к следующему этапу. Углуби текущий этап, попроси больше деталей или телесного отклика.\n"

    system_prompt = f"""Ты — агент ВЫРАВНИВАНИЯ системы AVATAR. Твой стиль: {sphere_style}.
Архетип: {arch_name} | Сфера: {sphere_data.get('name_ru', sphere)}
Уровень Хокинса: {hawkins_score} | Методология: {methodology['style']}

ГЛОБАЛЬНАЯ ЦЕЛЬ СЕССИИ (Хокинс-адаптация): {current_goal}

Стиль ответов: {methodology['style']}
Фокус: {methodology['focus']}
ИЗБЕГАЙ: {methodology['avoid']}

Ядро-убеждение: {core_belief or 'не определено'}
Паттерн тени: {shadow_pattern or 'не определён'}

---
КОНТЕКСТ ПРОШЛЫХ СЕССИЙ:
{history_context or 'История отсутствует.'}
---

ТЕКУЩИЙ ЭТАП {stage}/6: {stages.get(stage, '')}
{deepening_prompt}

ПРАВИЛА:
- Короткие, точные ответы (3-6 предложений)
- Один открытый вопрос в конце
- Только сенсорный, живой язык (без психоанализа)
- Если это этап 4, используй Светлую сторону Архетипа: {arch_light}
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-20:])
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

Транскрипт всех 5 слоев синхронизации:
{json.dumps(phase_data, ensure_ascii=False, indent=2)[:2500]}

ЗАДАЧА 1: Структурировать инсайты, фокусируясь на "Разломе" (Слой 3) и финальном "Дне" (Слой 4).
ЗАДАЧА 2: Проанализировать выборы и символы. Определи НАЙНИЗШУЮ проявленную точку по шкале Хокинса.

Отвечай строго в JSON формата:
{{
  "core_belief": "я не достоин финансового успеха",
  "shadow_pattern": "избегание + замирание",
  "body_anchor": "сжатие в груди",
  "projection": "зависть к успешным",
  "avoidance": "выбор безопасного пути",
  "key_choice_analysis": "анализ выбора на Разломе",
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


async def generate_alignment_summary(
    chat_history: list[dict],
    archetype_id: int,
    sphere: str
) -> dict:
    """
    Summarize alignment session for diary.
    Extracts: integration_plan, new_belief, final_insight.
    """
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})

    history_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in chat_history])

    prompt = f"""Ты — аналитик сессий трансформации AVATAR.
Твоя задача — подвести итог сессии выравнивания для записи в дневник.

Архетип: {archetype.get('name', '')} | Сфера: {sphere_data.get('name_ru', sphere)}

Диалог сессии:
{history_text[:4000]}

Выдели:
1. НОВОЕ УБЕЖДЕНИЕ: Короткая фраза, ставшая итогом сессии (якорь).
2. ПЛАН ВНЕДРЕНИЯ (Integration Plan): 1-3 конкретных действия в реальности на ближайшую неделю.
3. ГЛАВНЫЙ ИНСАЙТ: Глубинное осознание о работе паттерна.

Отвечай строго в JSON:
{{
  "new_belief": "я создаю свой мир через воображение",
  "integration_plan": "1. Утром визуализировать 5 минут... 2. Сказать 'нет' предложению...",
  "final_insight": "мой страх был лишь маской защиты..."
}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "new_belief": "",
            "integration_plan": "Продолжать наблюдение за собой.",
            "final_insight": ""
        }

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
    
    # Relax criteria for very high levels (they might be concise)
    # But for now, we want depth.
    
    return {
        "is_sufficient": is_sufficient,
        "reason": "depth_check_passed" if is_sufficient else "too_abstract_or_short"
    }

async def run_alignment_expert_analysis(
    chat_history: list[dict],
    archetype_id: int,
    sphere: str
) -> dict:
    """
    Final expert review of an Alignment Session transcript.
    Evaluates the actual transformation depth and final Hawkins state.
    """
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})
    
    transcript_text = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in chat_history])

    prompt = f"""Ты — старший аналитик системы AVATAR, эксперт по шкале Хокинса и глубинной трансформации.
Твоя задача — провести финальный аудит сессии ВЫРАВНИВАНИЯ.

Архетип: {archetype.get('name', '')} | Сфера: {sphere_data.get('name_ru', sphere)}

ТРАНСКРИПТ СЕССИИ:
{transcript_text[:5000]}

АЛГОРИТМ АУДИТА:
1. ОЦЕНКА ИСКРЕННОСТИ: Насколько ответы пользователя были формальными или они шли из чувств/тела?
2. ГЛУБИНА ПЕРЕЗАПИСИ (Слой 4): Смог ли пользователь реально увидеть и выбрать альтернативную реакцию?
3. ФИНАЛЬНЫЙ ВИБРАЦИОННЫЙ ОТКЛИК: Какое состояние зафиксировано в конце (Этап 5-6)?
4. ДИНАМИКА: С какого уровня Хокинса начали и к какому реально пришли (не верь автоматическому счетчику, замерь сам).

Отвечай строго в JSON:
{{
  "hawkins_score": 250,
  "hawkins_level": "Смелость",
  "dominant_emotion": "решимость",
  "transformation_depth": 8,
  "final_state_summary": "краткое описание достигнутого состояния",
  "is_shadow_integrated": true
}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "hawkins_score": 100,
            "hawkins_level": "Страх",
            "dominant_emotion": "не определено",
            "transformation_depth": 1,
            "final_state_summary": "Анализ не удался",
            "is_shadow_integrated": false
        }
