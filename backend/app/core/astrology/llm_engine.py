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
    Calls LLM to synthesize raw data into 12 detailed sphere descriptions.
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
            ]
        )
        content = response.choices[0].message.content
        
        # Cleanup markdown formatting if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        parsed_content = json.loads(content)
        # Ensure the expected key exists, or wrap the content if it's missing
        if "spheres_12" in parsed_content:
            return parsed_content
        else:
            return {"spheres_12": parsed_content}
    except Exception as e:
        print(f"Error in synthesize_sphere_descriptions: {e}")
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
