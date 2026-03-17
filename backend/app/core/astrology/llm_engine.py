import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

DEEP_SPHERE_PROMPT = """
РОЛЬ:
Ты — ВЕРХОВНЫЙ АСТРОПСИХОЛОГ. Твоя задача — провести глубочайший анализ ОДНОЙ конкретной сферы жизни на основе полных данных Натальной карты.

ЗАДАЧА:
Сфокусируйся исключительно на сфере: {sphere_name} ({sphere_desc})
1. Проанализируй все планеты, знаки и дома, имеющие отношение к этой сфере.
2. Проанализируй аспекты, влияющие на динамику в этой области.
3. Сформируй многогранную интерпретацию без ограничений по объему, но сохраняя высокую плотность смыслов.

ВЕРНИ ОТВЕТ В СТРОГОМ JSON СОГЛАСНО СХЕМЕ:
{{
  "status": "Архетипический маркер (2-4 слова, например: 'Пробуждающаяся Сила' или 'Кармический Узел')",
  "pithy_summary": "Суть сферы в 1-2 предложениях. Самое главное.",
  "psychological_portrait": {{
    "light": "Глубокий разбор Света: таланты, высшее предназначение в этой сфере, точки роста через радость (200-400 знаков).",
    "shadow": "Глубокий разбор Тени: бессознательные страхи, саботаж, родовые программы и слепые пятна (200-400 знаков)."
  }},
  "evolutionary_task": "Конкретный духовный и экзистенциальный урок этой сферы. Зачем это дано?",
  "life_hacks": ["Практический шаг 1", "Практический шаг 2", "Практический шаг 3"],
  "astrological_markers": ["Планета X в доме Y", "Аспект A к B", "Положение управителя"],
  "resonance_score": 0-100,
  "weighted_resonance": [
    {"archetype_id": 1, "weight": 95, "reason": "Управитель дома в экзальтации"},
    {"archetype_id": 7, "weight": 45, "reason": "Обитатель дома"}
  ]
}}


ЯЗЫК: Строго РУССКИЙ.
ТЕКСТ: Живой, глубокий, без "астрологического мусора". Фокус на психологии и трансформации.
"""

SPHERES_INFO = {
    "IDENTITY": "Я, маска, физическое тело, первое впечатление, базовая жизненная сила.",
    "RESOURCES": "Самооценка, деньги, личная энергия, таланты, которыми мы владеем.",
    "COMMUNICATION": "Интеллект, речь, ближайшее окружение, обучение, стиль мышления.",
    "ROOTS": "Фундамент, подсознание, род, дом, чувство безопасности.",
    "CREATIVITY": "Радость, созидание, любовь, дети, самовыражение через игру.",
    "SERVICE": "Работа, ежедневные обязанности, здоровье, критичность, мастерство.",
    "PARTNERSHIP": "Личные отношения, бизнес-партнеры, зеркала души, внешние враги.",
    "TRANSFORMATION": "Кризисы, чужие ресурсы, секс, мистика, выход за пределы.",
    "EXPANSION": "Мировоззрение, высшее образование, путешествия, идеология.",
    "STATUS": "Карьера, призвание, социальный успех, наши достижения.",
    "VISION": "Друзья, группы единомышленников, мечты, проекты будущего.",
    "SPIRIT": "Милосердие, тишина, божественная связь, завершение циклов."
}

async def synthesize_deep_sphere(sphere_key: str, chart_dict: dict, aspects_dict: list) -> dict:
    """
    Synthesizes a deep, granular description for a SINGLE sphere.
    """
    sphere_desc = SPHERES_INFO.get(sphere_key, "")
    prompt = DEEP_SPHERE_PROMPT.format(sphere_name=sphere_key, sphere_desc=sphere_desc)
    
    chart_json = json.dumps(chart_dict, ensure_ascii=False)
    aspects_json = json.dumps(aspects_dict, ensure_ascii=False)
    user_content = f"NATAL CHART DATA:\n{chart_json}\n\nASPECTS DATA:\n{aspects_json}"

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error in synthesize_deep_sphere for {sphere_key}: {e}")
        return {
            "status": "В обработке",
            "pithy_summary": "Глубинные данные формируются...",
            "psychological_portrait": {"light": "...", "shadow": "..."},
            "evolutionary_task": "...",
            "life_hacks": [],
            "astrological_markers": [],
            "resonance_score": 0,
            "weighted_resonance": []
        }


SPHERES_PROMPT = """
РОЛЬ:
Ты — МАСТЕР АСТРОЛОГИЧЕСКОГО СИНТЕЗА. Твоя задача — превратить «Сырые данные» (положения планет и аспекты) в поток глубоких аналитических озарений для 12 ключевых сфер жизни.

ЗАДАЧА:
1. Глубоко проанализируй предоставленный JSON Натальной карты (планеты, знаки, дома и аспекты).
2. Для каждой из 12 сфер проведи многомерный синтез.
3. Предоставь структурированный ответ для КАЖДОЙ сферы, содержащий:
   - interpretation: Краткое и емкое психологическое описание сферы (3-5 предложений). Пиши по сути, для быстрого ознакомления.
   - light: Главный талант или дар в этой области.
   - shadow: Основной вызов или ловушка.
   - astrological_markers: Краткий список ключевых показателей (планета в знаке/доме).

ПРИНЦИПЫ:
- КРАТКОСТЬ: Это первичный срез для быстрой загрузки. Не более 5 предложений в интерпретации.
- БЕЗ ЖАРГОНА: Используй живой человеческий язык.
- ЯЗЫК: Строго РУССКИЙ.

СФЕРЫ (МАППИНГ):
1. IDENTITY: Я, маска, физическое тело.
2. RESOURCES: Самооценка, деньги, энергия.
3. COMMUNICATION: Интеллект, окружение, обучение.
4. ROOTS: Фундамент, род, дом.
5. CREATIVITY: Радость, созидание, любовь.
6. SERVICE: Ритм, тело, работа.
7. PARTNERSHIP: Другой, зеркала, союзы.
8. TRANSFORMATION: Власть, тени, кризис.
9. EXPANSION: Горизонты, философия, мудрость.
10. STATUS: Призвание, роль, результаты.
11. VISION: Будущее, группы, мечты.
12. SPIRIT: Тишина, божественная связь.

ВЫВОД: Верни валидный JSON-объект с ключом "spheres_12".
"""

async def synthesize_sphere_descriptions(chart_dict: dict, aspects_dict: list) -> dict:
    """
    Calls LLM to synthesize raw data into 12 detailed sphere descriptions (L1 version).
    """
    chart_json = json.dumps(chart_dict, ensure_ascii=False)
    aspects_json = json.dumps(aspects_dict, ensure_ascii=False)
    user_content = f"NATAL CHART DATA:\n{chart_json}\n\nASPECTS DATA:\n{aspects_json}"

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SPHERES_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        parsed_content = json.loads(content)
        
        if "spheres_12" in parsed_content:
            return parsed_content
        else:
            return {"spheres_12": parsed_content}
    except Exception as e:
        print(f"Error in synthesize_sphere_descriptions: {e}")
        fallback = {s: {
            "interpretation": "Данные в процессе обработки...",
            "light": "В процессе...",
            "shadow": "В процессе...",
            "astrological_markers": "N/A"
        } for s in SPHERES_INFO.keys()}
        return {"spheres_12": fallback}
