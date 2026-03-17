import json
import os
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

DATA_DIR = settings.DATA_DIR

try:
    with open(os.path.join(DATA_DIR, "archetype_sphere_matrix.json"), "r", encoding="utf-8") as f:
        MATRIX_DATA = json.load(f)
except Exception:
    MATRIX_DATA = {}

ARCHETYPES = {
    int(arch_id): {
        "id": int(arch_id), 
        "name": data.get("_meta", {}).get("archetype_name", f"Архетип {arch_id}")
    } 
    for arch_id, data in MATRIX_DATA.items() if arch_id.isdigit()
}

with open(os.path.join(DATA_DIR, "spheres.json")) as f:
    SPHERES = {item["key"]: item for item in json.load(f)}
ARCHETYPE_IDS = list(range(22))



with open(os.path.join(DATA_DIR, "hawkins_scale.json")) as f:
    HAWKINS_SCALE = json.load(f)

SPHERE_AGENT_STYLES = {
    "IDENTITY": "зеркало",
    "RESOURCES": "практичный мудрец",
    "COMMUNICATION": "пытливый исследователь",
    "ROOTS": "мудрый старейшина",
    "CREATIVITY": "вдохновляющий творец",
    "SERVICE": "терпеливый мастер",
    "PARTNERSHIP": "тёплый честный друг",
    "TRANSFORMATION": "хранитель теней",
    "EXPANSION": "вдохновляющий стратег",
    "STATUS": "строгий наставник",
    "VISION": "футуролог-мечтатель",
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

LEVEL_GOALS = {
    "SURVIVAL": {"range": (0, 199), "goal": "Безопасность и Разрешение: Фокус на выдерживании эмоции и телесном присутствии. Не требуй быстрых решений."},
    "GROWTH": {"range": (200, 499), "goal": "Ответственность и Выбор: Фокус на идентификации паттерна и активном выборе новой реакции."},
    "PRESENCE": {"range": (500, 1000), "goal": "Наблюдение и Единство: Фокус на разотождествлении с паттерном и расширении сознания."},
}
