import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SPHERES_PROMPT = """
РОЛЬ:
Ты — МАСТЕР АСТРОЛОГИЧЕСКОГО СИНТЕЗА. Твоя задача — превратить «Сырые данные» (положения планет и аспекты) в поток глубоких аналитических озарений для 12 ключевых сфер жизни.

ЗАДАЧА:
1. Глубоко проанализируй предоставленный JSON Натальной карты (планеты, знаки, дома и аспекты).
2. Для каждой из 12 сфер проведи многомерный синтез.
3. Предоставь структурированный ответ для КАЖДОЙ сферы, содержащий:
   - interpretation: Глубокое, профессиональное психологическое и эволюционное описание сферы (8-10 предложений). Пиши плотно, без воды, раскрывая причинно-следственные связи.
   - light: Высший потенциал, таланты и дары души в этой области.
   - shadow: Страхи, искажения, кармические ловушки и точки потери энергии.
   - astrological_markers: Краткое пояснение, какие планеты, знаки и аспекты сформировали этот вывод (для прозрачности).

ПРИНЦИПЫ:
- БЕЗ ЖАРГОНА В ИНТЕРПРЕТАЦИИ: Используй ясный, живой и профессиональный психологический язык.
- ЭКСПЕРТНЫЙ УРОВЕНЬ: Не просто перечисляй положения. Синтезируй управителя дома, планеты в доме и мажорные аспекты.
- БАЛАНС: Будь честен в отношении вызовов, но не впадай в фатализм.
- ЯЗЫК: Весь контент должен быть СТРОГО на РУССКОМ языке.

СФЕРЫ (МАППИНГ):
1. IDENTITY: Я, маска, физическое тело, первое впечатление.
2. RESOURCES: Самооценка, деньги, врожденные таланты, жизненная энергия.
3. COMMUNICATION: Интеллект, окружение, обучение, короткие пути.
4. ROOTS: Фундамент, род, дом, внутренняя безопасность.
5. CREATIVITY: Радость, созидание, любовь, самовыражение, огонь.
6. SERVICE: Дневной ритм, тело, работа, дисциплина.
7. PARTNERSHIP: Другой, зеркала, контракты, союзы.
8. TRANSFORMATION: Глубинная власть, тени, алхимия кризиса.
9. EXPANSION: Расширение горизонтов, философия, мудрость, длинные пути.
10. STATUS: Социальный пик, призвание, публичная роль, результаты.
11. VISION: Будущее, групповое сознание, братство, мечты.
12. SPIRIT: Одиночество, завершение, божественная связь, тишина.

ВЫВОД: Верни валидный JSON-объект с ключом "spheres_12".
"""

async def synthesize_sphere_descriptions(chart_dict: dict, aspects_dict: list) -> dict:
    """
    Analyzes the natal chart and generates a high-detail structured analysis for all 12 spheres.
    """
    raw_data = {
        "chart": chart_dict,
        "aspects": aspects_dict
    }
    
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SPHERES_PROMPT},
            {"role": "user", "content": f"THE RAIN DATA (Natal Chart):\n{json.dumps(raw_data, ensure_ascii=False)}"}
        ],
        response_format={"type": "json_object"},
    )
    
    try:
        content = json.loads(response.choices[0].message.content)
        # Ensure the expected key exists
        if "spheres_12" in content:
            return content
        else:
            # Fallback if AI missed the top-level key
            return {"spheres_12": content}
    except Exception as e:
        print(f"Error in Master of Synthesis synthesis: {e}")
        sphere_keys = [
            "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
            "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
            "EXPANSION", "STATUS", "VISION", "SPIRIT"
        ]
        fallback = {s: {
            "interpretation": "Данные в процессе обработки...",
            "light": "В процессе...",
            "shadow": "В процессе...",
            "astrological_markers": "N/A"
        } for s in sphere_keys}
        return {"spheres_12": fallback}
