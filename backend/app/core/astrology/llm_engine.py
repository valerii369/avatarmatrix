import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SPHERES_PROMPT = """Ты — ВЕРХОВНЫЙ AI-АЛХИМИК системы AVATAR. 
Тебе передана детальная натальная карта пользователя (JSON).

Твоя задача — провести глубокий многомерный синтез и описать состояние пользователя в 12 Сферах Жизни.
Для каждой сферы создай качественное, психологически точное и метафоричное описание (3-5 предложений). 

ПРАВИЛА:
1. Синтезируй планету в доме + планету в знаке + аспекты.
2. Указывай СВЕТ (потенциал) и ТЕНЬ (риски/страхи) для каждой сферы.
3. Используй глубокий, качественный русский язык.

СПИСОК СФЕР:
- IDENTITY: Личность, маска, первое впечатление.
- RESOURCES: Ресурсы, самооценка, деньги, таланты.
- COMMUNICATION: Связи, среда, обучение, информация.
- ROOTS: Фундамент, род, дом, безопасность.
- CREATIVITY: Радость, созидание, любовь, самовыражение.
- SERVICE: Здоровье, дисциплина, ежедневный труд, тело.
- PARTNERSHIP: Отражение в других, союзы, зеркала.
- TRANSFORMATION: Кризисы, алхимия тени, глубокая мощь.
- EXPANSION: Смыслы, вера, горизонты, мудрость.
- STATUS: Социальный пик, карьера, амбиции, статус.
- VISION: Будущее, коллективный разум, мечты, группы.
- SPIRIT: Духовность, тишина, завершение, целостность.

ОТВЕТ ДОЛЖЕН БЫТЬ СТРОГО В ВИДЕ JSON с 12 ключами.
"""

async def synthesize_sphere_descriptions(chart_dict: dict, aspects_dict: list) -> dict:
    """
    Analyzes the natal chart and generates a descriptive text for each of the 12 spheres.
    """
    raw_data = {
        "chart": chart_dict,
        "aspects": aspects_dict
    }
    
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SPHERES_PROMPT},
            {"role": "user", "content": f"Натальная карта:\n{json.dumps(raw_data, ensure_ascii=False)}"}
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    
    try:
        content = json.loads(response.choices[0].message.content)
        return content
    except Exception as e:
        print(f"Error parsing LLM response for 12 sphere descriptions: {e}")
        sphere_keys = [
            "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
            "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
            "EXPANSION", "STATUS", "VISION", "SPIRIT"
        ]
        return {sphere: "Данные в процессе обработки..." for sphere in sphere_keys}
