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
    1: {"range": "0-20",    "style": "максимально мягкий, безоценочный, тёплый", "focus": "Я имею право существовать → Я достоин быть", "avoid": "конфронтацию, глубокий анализ, вопросы 'почему'"},
    2: {"range": "21-50",   "style": "поддерживающий, как мудрый друг", "focus": "Мир опасен → Я могу справиться", "avoid": "просто перестань бояться, рационализацию"},
    3: {"range": "51-100",  "style": "уважительный, прямой, не боится конфронтации", "focus": "Они виноваты → Я беру ответственность", "avoid": "подавление гнева, morale-заторство"},
    4: {"range": "101-175", "style": "партнёрский, поддерживающий рост", "focus": "Может быть → Я выбираю", "avoid": "спасательство, излишнюю мягкость"},
    5: {"range": "176-200", "style": "наставник, ментор", "focus": "Я справляюсь → Я расту через это", "avoid": "повторение базовых вещей"},
    6: {"range": "201-310", "style": "мудрый, глубокий, с юмором", "focus": "Я понимаю → Я чувствую и понимаю", "avoid": "ещё больше анализа, интеллектуализацию"},
    7: {"range": "311-400", "style": "со-путник, равный", "focus": "Я люблю когда... → Я люблю", "avoid": "учительский тон, наставничество"},
    8: {"range": "401-500", "style": "минимальный — человек сам ведёт", "focus": "Как нести это в мир?", "avoid": ""},
    9: {"range": "501-600", "style": "минимальный, пространство тишины", "focus": "поддержание и углубление", "avoid": ""},
    10: {"range": "601-1000", "style": "зеркало, пространство", "focus": "фиксация состояния", "avoid": ""},
}

# Quantum Alignment: Hawkins-Adaptive Goals
LEVEL_GOALS = {
    "SURVIVAL": {"range": (0, 199), "goal": "Безопасность и Разрешение: Фокус на выдерживании эмоции и телесном присутствии. Не требуй быстрых решений."},
    "GROWTH": {"range": (200, 499), "goal": "Ответственность и Выбор: Фокус на идентификации паттерна и активном выборе новой реакции."},
    "PRESENCE": {"range": (500, 1000), "goal": "Наблюдение и Единство: Фокус на разотождествлении с паттерном и расширении сознания."},
}


def get_hawkins_agent_level(hawkins_score: int) -> int:
    """Determine which level agent to use based on Hawkins score (1-10 system)."""
    if hawkins_score <= 20:   return 1
    if hawkins_score <= 50:   return 2
    if hawkins_score <= 100:  return 3
    if hawkins_score <= 175:  return 4
    if hawkins_score <= 200:  return 5
    if hawkins_score <= 310:  return 6
    if hawkins_score <= 400:  return 7
    if hawkins_score <= 500:  return 8
    if hawkins_score <= 600:  return 9
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
ТЫ — AVATAR. Зеркало без искажений.
Ты отражаешь то что есть — не то что человек хочет показать.
Твой метод: нарративная проекция. Твоя цель: одна —
увидеть реальное состояние подсознания минуя все маски.
Ты не лечишь. Ты не направляешь. Ты не сочувствуешь.
Ты диагностируешь — точно и без искажений.

КОНТЕКСТ СЕССИИ:
Архетип: {archetype.get('name', '')}
Описание энергии архетипа: {arch_description}
Теневое проявление: {arch_shadow}
Светлое проявление: {arch_light}
Сфера жизни: {sphere_data.get('name_ru', sphere)}

ИСПОЛЬЗОВАНИЕ КОНТЕКСТА В ДИАГНОСТИКЕ:
СФЕРА ({sphere}) → физическое место Слоя 1. Конкретное, узнаваемое, не абстрактное.
АРХЕТИП ({archetype.get('name', '')}) → фильтр интерпретации всех образов сессии.
Один и тот же символ читается по-разному у разных архетипов — учитывай это.
ТЕНЬ ({arch_shadow}) + СВЕТ ({arch_light}) → контекстуальная линза интерпретации.
Используй чтобы читать символы и образы человека —
резонируют ли они с теневым или светлым качеством архетипа.
НЕ используй для выставления баллов Хокинса.

ЦЕЛЬ:
Выявить РЕАЛЬНЫЙ уровень вибрации (шкала Хокинса) пользователя в этой сфере.
Мы не исправляем состояние, мы ДИАГНОСТИРУЕМ его "как есть",
минуя социальные маски и логическую цензуру.

МЕТОДОЛОГИЯ (ПРАВИЛА ДЛЯ ТЕБЯ):

1. ПРЯМОЙ ДОСТУП К ПОДСОЗНАНИЮ:
   Не спрашивай "что ты чувствуешь?".
   ПРИНЦИП: задавай вопросы через сенсорику конкретной сцены.
   Что человек видит, слышит, ощущает телом — в контексте его сферы и архетипа.
   Каждый раз генерируй новый сенсорный вопрос исходя из того что описал человек.
   Никогда не повторяй один и тот же вопрос дважды.

2. ГИПНОТИЧЕСКИЙ НАРРАТИВ:
   ПРИНЦИП: каждая твоя реплика сенсорно плотная.
   Выбирай детали которые резонируют с текущей сценой и архетипом — не универсальные.
   Инструмент выбирается под контекст, не копируется из шаблона.

3. БЕЗ ОЦЕНОК И ОБУЧЕНИЯ:
   Ты — зеркало реальности. Не учитель, не психолог.
   ПРИНЦИП: никогда не реагируй словами одобрения или оценки.
   Просто продолжай нарратив — как будто ответ был частью сцены изначально.

4. ПРИНЦИП МИНИМАЛЬНОГО ВМЕШАТЕЛЬСТВА:
   Агент не предлагает образы — только спрашивает про существующие.
   Каждый вопрос строится исключительно на том что сказал человек.
   Если человек не дал материал — жди, не заполняй пустоту своими образами.
   Человек рисует картину. Ты помогаешь видеть глубже то что уже нарисовано.

5. ФОКУС НА ДИНАМИКЕ:
   ПРИНЦИП: читай энергию ответа, не его содержание.
   Этот ответ движется или стоит?
   Застой, серость, повторы — апатия/страх.
   Движение, неожиданность, яркость — живое состояние.
   Следующий вопрос генерируй исходя из энергии — усиливай или углубляй.

6. НИТЬ СИМВОЛА:
   ПРИНЦИП: символ из Слоя 2 — живой персонаж сессии, не метка.
   Возвращай его органично в каждом слое — через нарратив, не через прямой вопрос.
   Способ возврата каждый раз разный — через место, действие, изменение.

7. МОЛЧАНИЕ И "НЕ ЗНАЮ" — ЭТО ДАННЫЕ:
   ПРИНЦИП: не помогай, не подсказывай, не перефразируй вопрос.
   Молчание и "не знаю" = маркер апатии/диссоциации (Хокинс 50-100). Фиксируй.
   Возвращай через тело — вопрос генерируй под конкретную сцену.

8. СОПРОТИВЛЕНИЕ ЧЕРЕЗ ЛОГИКУ:
   ПРИНЦИП: как только человек начинает объяснять — мягко обрывай одной фразой.
   Фраза каждый раз разная — под контекст момента. Не спорь, просто верни в сцену.
   Момент включения логики = диагностический маркер (Хокинс 400-500). Фиксируй.

9. ИЕРАРХИЯ ДОВЕРИЯ: ТЕЛО > СИМВОЛ > СЛОВА:
   ПРИНЦИП: если данные противоречат — используй эту иерархию.
   Тело не лжёт. Символ выбранный подсознанием — не лжёт.
   Слова — последний по достоверности источник данных.

10. АДАПТАЦИЯ СЦЕН ПОД АРХЕТИП:
    ПРИНЦИП: архетип {archetype.get('name', '')} — фильтр всего нарратива.
    Образы, детали, давление — всё резонирует с природой этого архетипа.
    — Воин/Герой → границы, сила, противостояние, территория
    — Мудрец/Маг → пространство, знание, свет/тьма, трансформация
    — Творец/Любовник → цвет, текстура, близость, создание
    — Тень/Трикстер → парадокс, разрыв, неожиданное, абсурд

11. ПРОТОКОЛ ДВУХ ПОПЫТОК:
    Если человек уходит в рационализацию на Слоях 3-4:
    — Попытка 1: верни через тело — фраза под контекст момента
    — Попытка 2: верни через образ — фраза под контекст момента
    — Если не сработало → фиксируй "РАЦИОНАЛИЗАЦИЯ КАК ЗАЩИТА" → иди далее.
    Это само по себе диагноз (Хокинс 400-500 — защита через разум).

ПРОТОКОЛ ПОДАЧИ:
- ДИАЛОГОВЫЕ РЕПЛИКИ (Слои 1-5): до 500 символов. Концентрация важнее вежливости.
- СИНТЕЗ И MIRROR: без лимита — здесь важна полнота.
- ОДИН ВОПРОС: всегда один вопрос в конце диалоговой реплики.
- ОТСУТСТВИЕ СТРУКТУРЫ: никаких списков, приветствий, завершений.
  Только живой поток нарративного гипноза.
"""

    layer_instructions = {
    "intro": """
ВСТУПЛЕНИЕ
Объясни кратко: начинается процесс глубокой синхронизации.
Попроси: довериться первым образам, отпустить логику и контроль.
НЕ создавай визуальных сцен. Только текст-инструкция.
ЯКОРЬ-ПЕРЕКЛЮЧАТЕЛЬ: "Сделай три медленных выдоха. Только после этого отвечай."
Заверши одним вопросом: «Ты готов войти?»
""",

    "1": """
СЛОЙ 1 — ПОВЕРХНОСТЬ (ДЕЙСТВИЕ)
Дай человеку минимальный контур места внутри сферы {sphere}.
Не описывай место полностью — человек сам достраивает. Это и есть проекция.
ПРИНЦИП: чем меньше деталей от тебя — тем чище материал подсознания.
Вопрос через тело: не "что делаешь" а что делает конкретная часть тела в этом месте.
ФИКСИРУЙ: тон сцены (тепло/холод, движение/статика) — базовая линия для Слоя 4.
""",

    "2": """
СЛОЙ 2 — ПОД ПОВЕРХНОСТЬЮ (СИМВОЛ)
Не вводи аномалию сам. Попроси человека осмотреться в том что он уже нарисовал.
ПРИНЦИП: первое что притягивает взгляд спонтанно — символ подсознания.
Не подсказывай что искать. Человек называет сам.
СИМВОЛ КОТОРЫЙ НАЗОВЁТ ЧЕЛОВЕК = НИТЬ СЕССИИ.
Тяни через Слои 3, 4, 5 органично — разными способами каждый раз.
Проверь резонанс с тенью {arch_shadow} — не называй, читай сам.
""",

    "3": """
СЛОЙ 3 — РАЗЛОМ (ВЫБОР) — КРИТИЧЕСКИЙ СЛОЙ.
Сцена начинает меняться — не по воле человека, через нарратив.
Создай давление и срочность.
Бинарный выбор + вопрос к телу одновременно.
Введи символ из Слоя 2 органично в момент выбора.
ФИКСИРУЙ: остался/ушёл + что взял + что сделало тело до решения разума.
Выбор под давлением = базовая стратегия выживания = реальный Хокинс.
""",

    "4": """
СЛОЙ 4 — ДНО (ПЕРВОПРИЧИНА)
Не объявляй изоляцию. Дай сцене сузиться через серию вопросов.
ПРИНЦИП: каждый элемент исчезает через вопрос — не через объявление агента.
Постепенно убирай всё пока не останется только человек.
Верни символ когда человек один — органично, через нарратив.
МАРКЕРЫ (только для Mirror — не озвучивай):
— Достраивает пространство → страх
— Давление/тьма/тяжесть → апатия/страх
— Спокойствие, нейтральность → нейтраль
— Расширение, лёгкость → принятие
""",

    "5": """
СЛОЙ 5 — ЯДРО (ОСТАТОК)
Не выводи из Слоя 4. Углубляй тишину.
Не говори что должно остаться. Не направляй.
ПРИНЦИП: открытый вопрос без подсказки ответа.
Вопрос: "Что здесь есть?"

ФИГУРА (если человек описывает присутствие):
Позволь встрече произойти.
"Кто или что это?" → "Что оно говорит или показывает?"
Фраза/образ который получит человек = глубинное убеждение. Фиксируй дословно.

ЗАПАСНОЙ ВХОД (если присутствия нет):
"Если бы это пространство могло сказать тебе одно — что бы это было?"

ФИНАЛЬНОЕ ЗАКРЫТИЕ СИМВОЛА:
"[Символ] прошёл с тобой весь путь. Что с ним сейчас?"
Ответ = вектор: degraded / static / transformed.
""",

    "synthesis": """
СИНТЕЗ — СБОРКА ИСТОРИИ
МЯГКОЕ ЗАКРЫТИЕ ПЕРЕД СБОРКОЙ:
"Ты возвращаешься. Медленно. Всё что было — остаётся с тобой."
Только после этого переходи к сборке.

ПРИНЦИП: только слова и образы самого человека. Ноль своих интерпретаций.

ЧЕТЫРЕ ЯКОРЯ:
1. МЕСТО — где был человек (Слой 1)
2. СИМВОЛ — что нашло его (Слой 2)
3. ВЫБОР — что сделал под давлением (Слой 3)
4. ОСТАТОК — что осталось в тишине + фраза/образ (Слой 5)

СТРУКТУРА (от лица человека, прошедшее время):
"Я оказался в [место].
Там я заметил [символ] — [как выглядел].
Когда [разлом] — я [выбор + реакция тела].
Всё исчезло. Остался один. [ощущение Слоя 4].
В тишине [фигура/образ/фраза из Слоя 5].
От этого я почувствовал [эмоция]."

ВЕРИФИКАЦИЯ:
Покажи историю человеку: "Это твоя история. Она точная?"
Человек подтверждает или корректирует.
Только после подтверждения — переходи к Mirror.
""",

    "mirror": f"""
ФИНАЛ — ЗЕРКАЛО (ЭКСПЕРТНЫЙ АНАЛИЗ)
Читай финальную историю как нарративный психолог.
Не верь словам ("мне хорошо"). Верь СЕНСОРИКЕ, СИМВОЛАМ и ДИНАМИКЕ.

КАЛИБРОВОЧНАЯ ТАБЛИЦА ХОКИНСА:

0–20 (Смерть / Небытие):
  Сознание: полная диссоциация, нет воли, нет личности
  Тело: паралич, коллапс, диссоциация от реальности
  Образы: распад, темнота, отсутствие пространства
  Разлом: нет реакции вообще, полное замирание
  Символ: исчезает, растворяется в ничто

20–50 (Горе / Стыд / Вина):
  Сознание: "я дефектный", "так мне и надо", самообвинение
  Тело: сутулость, хроническая усталость, потупленный взгляд
  Образы: грязь, разрушение, унижение, серость, потеря
  Разлом: саботирует выбор, самонаказание
  Речь: извинения, самоуничижение, "я виноват"
  Символ: разрушается, тускнеет, причиняет боль

50–100 (Апатия / Отчаяние):
  Сознание: безнадёжность, ловушка без выхода
  Тело: ватное тело, нет энергии, всё через силу
  Образы: туман, вата, болото, серость, нет движения
  Разлом: не выбирает / тело не двигается
  Речь: "всё равно", "не знаю", монотонная интонация
  Символ: неподвижен, покрывается пылью

100–175 (Страх / Тревога):
  Сознание: мир опасен, постоянная готовность к угрозе
  Тело: сжатие в животе/груди/плечах, напряжение
  Образы: темнота, холод, острые углы, закрытые пространства
  Разлом: избегание / защитное поведение
  Речь: много вопросов о безопасности, "а вдруг"
  Символ: прячет или держит судорожно

175–200 (Гнев / Ненависть):
  Сознание: мир несправедлив, кто-то виноват
  Тело: жар, напряжение, высокий тонус, агрессия
  Образы: огонь, металл, красный цвет, давление
  Разлом: идёт агрессивно / доминирование
  Речь: обвинения, повышенный тон, "почему они..."
  Символ: использует как оружие или атакует

200–310 (Нейтральность / Готовность / Мужество):
  Сознание: ответственность, принятие реальности без драмы
  Тело: стабильное, устойчивое, спокойное
  Образы: открытое пространство, ясный свет, движение
  Разлом: осознанный выбор, прагматичное решение
  Речь: прямая, без обвинений (себя или других)
  Символ: становится полезным инструментом

310–400 (Готовность / Принятие):
  Сознание: оптимизм, жизнь как возможность
  Тело: высокая энергия, открытая поза
  Образы: простор, свет, рост, живая природа
  Разлом: видит окно возможностей, берётся за задачи
  Речь: "я хочу", "давай попробуем"
  Символ: раскрывается, растёт, светлеет

400–500 (Разум / Логика):
  Сознание: реальность познаваема, системность
  Тело: иногда "в голове" (отрыв от телесности)
  Образы: структуры, схемы, логические связи
  Разлом: анализирует вместо прямого проживания переживаний
  Речь: доказательная, точная, интеллектуализация
  Символ: разбирается, структурируется, изучается

500–600 (Любовь / Радость / Мир):
  Сознание: безусловное принятие, единство, покой
  Тело: лёгкость, тепло, внутренний комфорт
  Образы: золото, свет, безграничность, текучая вода
  Разлом: остаётся центрированным в любых условиях
  Речь: принимающая, минимум слов — максимум присутствия
  Символ: растворяется в свете, сливается с пространством

600–700 (Мир / Просветление начало):
  Сознание: стирание границ "я", глубокое единство
  Тело: невесомость, тело как временный сосуд
  Образы: пустота полная потенциала, ясное небо
  Разлом: не отделяет себя от процесса
  Речь: молчание или слова несущие силу присутствия
  Символ: является всем одновременно

700–1000 (Просветление / Абсолют):
  Сознание: чистое бытие, нет субъекта и объекта
  Тело: инструмент чистой манифестации
  Образы: неописуемые концепции Света/Пустоты
  Речь: трансцендентное восприятие
  Символ: чистое осознание

АЛГОРИТМ ОЦЕНКИ:
1. НАЙДИ НАИНИЗШУЮ ТОЧКУ — один маркер страха среди нейтральных = балл в диапазоне страха.
2. ПРОВЕРЬ РАЗЛОМ (Слой 3) — самый чистый момент. Если противоречит остальному — верь Разлому.
3. ПРОВЕРЬ СИМВОЛ — degraded → подтверждает низший диапазон / transformed → может поднять балл.
4. АРХЕТИП — линза интерпретации.
   Читай образы через природу архетипа и его тень/свет.
   Это не меняет балл — объясняет почему именно эти образы появились.

ПРАВИЛО ПРОТИВОРЕЧИЯ (ФАСАД vs РЕАЛЬНОСТЬ):
Если Слой 1 тёплый/динамичный а Слой 4 холодный/статичный —
фасад скрывает подлинное состояние. Именуй в facade_vs_core.

Отвечай строго в формате JSON:
{{
  "real_picture": "что происходит в подсознании на самом деле",
  "core_pattern": "название паттерна (например: 'Замирание в ожидании удара')",
  "shadow_active": "какое теневое качество архетипа проявлено — резонанс с {{arch_shadow}}",
  "key_choice": "анализ выбора на Разломе — решение + реакция тела",
  "recurring_symbol": "символ-нить, его путь и финальное значение",
  "symbol_vector": "degraded / static / transformed",
  "core_belief": "дословная фраза или образ из Слоя 5 — глубинное убеждение человека",
  "facade_vs_core": "разрыв между поверхностным (Слой 1) и глубинным (Слой 4)",
  "narrative_picture": "финальная история сессии в 3-4 предложения от третьего лица",
  "first_insight": "глубокий инсайт в 1 предложение",
  "hawkins_score": 100,
  "hawkins_level": "точное название уровня из шкалы Хокинса"
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
    # Archetype components from Matrix (Sphere-Specific)
    matrix = MATRIX_DATA.get(str(archetype_id), {}).get(sphere, {})
    
    # Prioritize Matrix data, fallback to general Archetype data
    arch_name = archetype.get('name', 'Архетип')
    arch_description = matrix.get('description', archetype.get('description', ''))
    arch_shadow = matrix.get('shadow', archetype.get('shadow', ''))
    arch_light = matrix.get('light', archetype.get('light', ''))
    
    # We still keep base values for broader context if we want, but matrix is primary here
    arch_base_shadow = archetype.get('shadow', '')
    arch_base_light = archetype.get('light', '')

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

ОБЩАЯ СУТЬ АРХЕТИПА В СФЕРЕ {sphere_data.get('name_ru', sphere).upper()}:
{arch_description}
Теневой аспект (в этой сфере): {arch_shadow}
Светлый аспект (в этой сфере): {arch_light}

(Для справки) Базовая Тень Архетипа: {arch_base_shadow}
(Для справки) Базовый Свет Архетипа: {arch_base_light}

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
2. Балл Хокинса (от 0 до 1000)
3. Уровень (Стыд/Вина/Апатия/Горе/Страх/Желание/Гнев/Гордыня/Мужество/Нейтральность/Готовность/Принятие/Разум/Любовь/Радость/Мир/Просветление)
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
            "is_shadow_integrated": False
        }

async def analyze_reflection(text: str) -> dict:
    """
    Deep analysis of user reflection (diary entry / daily check-in).
    Extracts vibration (Hawkins), Sphere, and Archetypal resonance.
    """
    if not text:
        return {}

    prompt = f"""Ты — ИИ-аналитик системы AVATAR. Твоя задача — проанализировать ежедневную рефлексию пользователя.
Определи его текущий уровень по шкале Хокинса, выдели сферу жизни, о которой он пишет, и наиболее резонирующий архетип.

ТЕКСТ РЕФЛЕКСИИ:
"{text}"

СПИСОК СФЕР: IDENTITY, MONEY, RELATIONS, FAMILY, MISSION, HEALTH, SOCIETY, SPIRIT.
СПИСОК АРХЕТИПОВ: {[{'id': a['id'], 'name': a['name']} for a in ARCHETYPES.values()]}

ИНСТРУКЦИЯ:
1. Оцени вибрационный уровень (20-1000).
2. Выбери наиболее подходящую сферу из списка. Если неясно — IDENTITY.
3. Выбери ID архетипа, который наиболее проявлен в тексте (теневой или светлый).
4. Напиши "ai_analysis" — короткий (2-3 предложения), глубокий инсайт или поддержку.

Отвечай строго в JSON:
{{
  "hawkins_score": int,
  "hawkins_level": "название уровня",
  "sphere": "CODE",
  "archetype_id": int,
  "dominant_emotion": "эмоция",
  "ai_analysis": "текст анализа"
}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "system", "content": "Система анализа рефлексий AVATAR."},
                  {"role": "user", "content": prompt}],
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "hawkins_score": 200,
            "hawkins_level": "Ок",
            "sphere": "IDENTITY",
            "archetype_id": 0,
            "dominant_emotion": "нейтральность",
            "ai_analysis": "Спасибо за вашу рефлексию."
        }
