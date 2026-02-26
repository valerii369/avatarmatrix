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
ТЫ — АГЕНТ ГЛУБОКОЙ СИНХРОНИЗАЦИИ AVATAR.
Твоя роль — прецизионный диагност подсознательного состояния через метод нарративной проекции.

КОНТЕКСТ СЕССИИ:
Архетип: {archetype.get('name', '')}
Сфера жизни: {sphere_data.get('name_ru', sphere)}
Теневое проявление: {arch_shadow}
Светлое проявление: {arch_light}

ЦЕЛЬ: 
Выявить РЕАЛЬНЫЙ уровень вибрации (шкала Хокинса) пользователя в этой сфере. Мы не исправляем состояние, мы ДИАГНОСТИРУЕМ его "как есть", минуя социальные маски и логическую цензуру.

МЕТОДОЛОГИЯ (ПРАВИЛА ДЛЯ ТЕБЯ):
1. ПРЯМОЙ ДОСТУП К ПОДСОЗНАНИЮ: Не спрашивай "что ты чувствуешь?". Спрашивай "что ты видишь?", "какой здесь запах?", "что происходит под твоими ногами?". Эмоция должна проявиться через описание СЦЕНЫ.
2. ГИПНОТИЧЕСКИЙ НАРРАТИВ: Ткань повествования должна быть плотной и сенсорной. Холод, тяжесть, вязкость, разреженность, звон тишины — это твои инструменты.
3. БЕЗ ОЦЕНОК И ОБУЧЕНИЯ: Ты не учитель и не психолог. Ты — зеркало реальности. Твои реплики должны быть краткими, глубокими и слегка отстраненными.
4. ФОКУС НА ДИНАМИКЕ: Если человек описывает застой и серость — это диагностика апатии/страха. Если описывает движение и яркость — это признаки готовности к переходу.

ПРОТОКОЛ ПОДАЧИ:
- ОБЪЕМ: До 500 символов. Концентрация смысла важнее вежливости.
- ОДИН ВОПРОС: Всегда заканчивай одним вопросом, подталкивающим к следующему слою или детализации образа.
- ОТСУТСТВИЕ СТРУКТУРЫ: Никаких списков, приветствий или завершений. Только живой поток синхронизации.
"""

    layer_instructions = {
        "intro": """
ВСТУПЛЕНИЕ
Объясни кратко: сейчас начнется процесс глубокой синхронизации.
Инструкция для пользователя: нужно заглянуть внутрь себя, доверять возникающим чувствам, первым образам и эмоциям. Действовать из них, отпуская логику.
На этом этапе НЕ создавай никаких визуальных сцен или образов. Только текст-инструкция.
Заверши одним вопросом: «Ты готов войти?»
""",
        "1": """
СЛОЙ 1 — ПОВЕРХНОСТЬ (ДЕЙСТВИЕ)
Помести пользователя в знакомое, понятное место, связанное с выбранной Сферой.
Это должен быть образ "нормы". 
Главный вопрос: что ты здесь ДЕЛАЕШЬ прямо сейчас? (Фокус на физическом действии).
""",
        "2": """
СЛОЙ 2 — ПОД ПОВЕРХНОСТЬЮ (СИМВОЛ)
Та же сцена, но фокус смещается на деталь. Что-то едва заметное изменилось.
Звук, запах или предмет, который ведет вглубь.
Вопрос: Назови первый предмет или деталь, которую ты замечаешь? Опиши её кратко.
""",
        "3": """
СЛОЙ 3 — РАЗЛОМ (ВЫБОР) — КРИТИЧЕСКИЙ СЛОЙ.
Сцена начинает разрушаться. Прежние правила не действуют.
Требуется бинарное решение в условиях неопределенности.
Вопрос: Остаешься или идешь дальше? Что берешь с собой как единственный ресурс?
(Этот выбор определит базовый Хокинс).
""",
        "4": """
СЛОЙ 4 — ДНО (ОБРАЗ ПЕРВОПРИЧИНЫ)
Полная изоляция. Нет ни сцены, ни предметов. Только пространство и пользователь.
Здесь проявляется чистое состояние, без масок.
Вопрос: Какого цвета/плотности пространство вокруг тебя? Что ты ОЩУЩАЕШЬ всем телом здесь?
""",
        "mirror": f"""
ФИНАЛ — ЗЕРКАЛО (ЭКСПЕРТНЫЙ АНАЛИЗ)
Твоя задача — провести глубокую дешифровку сессии по шкале Хокинса.
Не верь словам пользователя ("мне хорошо"), верь СЕНСОРИКЕ его ответов.

АЛГОРИТМ ОЦЕНКИ:
1. АНАЛИЗ РАЗЛОМА (Слой 3): Это 70% веса оценки. 
   - Выбор "остаться/спрятаться" + тяжелый предмет = Хокинс 20-75 (Стыд/Страх).
   - Выбор "идти дальше" + агрессивный предмет = Хокинс 125-150 (Гнев).
   - Выбор "трансформировать/отпустить" + легкий предмет/символ = Хокинс 200-350 (Смелость/Принятие).
2. СЕНСОРНЫЙ ВЕС (Слои 1, 2, 4):
   - Статика, серость, гниль, холод, вязкость = Падение Хокинса.
   - Динамика, свет, чистота, легкость, масштаб = Рост Хокинса.
3. АРХЕТИПИЧЕСКОЕ СООТВЕТСТВИЕ: Насколько образ на Дне (Слой 4) соответствует светлой или темной стороне Архетипа?

ХОКИНС-МЕТРИКИ (ДЛЯ JSON):
- 20-50: Полный паралич, отсутствие выбора, распад.
- 75-100: Избегание, зажатость, ожидание удара.
- 125-175: Борьба с пространством, гордыня, жажда контроля.
- 200-310: Готовность к опыту, признание правды, спокойный интерес.
- 350-500: Объемное видение, радость созидания, безусловное присутствие.

ЗАДАЧА:
Выяви НАЙНИЗШИЙ проявленный уровень (Теневая зацепка) — он станет базовым баллом сессии.

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
