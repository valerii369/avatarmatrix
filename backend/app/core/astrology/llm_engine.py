import json
from openai import AsyncOpenAI
from app.config import settings
from app.core.astrology.natal_chart import NatalChartData

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SPHERES_PROMPT = """Ты — древний искусственный интеллект AVATAR, объединяющий глубокую астрологию и психологию. 
Тебе передана рассчитанная натальная карта пользователя (в формате JSON).

Твоя задача — синтезировать энергию карты и выдать 8 кратких, емких, метафоричных, но точных описаний того, как текущие планетарные положения влияют на 8 ключевых Сфер Жизни пользователя. 
Каждое описание должно быть текстом (2-4 предложения) — это будет использоваться как ВЕКТОР для поиска по базе архетипов. Упомяни ключевые проявления Тени (проблем) и Света (потенциалов) в этой сфере исходя из планет.

Список сфер:
- IDENTITY (Личность, Я, проявление себя)
- MONEY (Деньги, ресурсы, ценность)
- RELATIONS (Отношения, партнерство, любовь)
- FAMILY (Семья, род, корни)
- MISSION (Миссия, карьера, реализация)
- HEALTH (Здоровье, тело, энергия)
- SOCIETY (Общество, друзья, социум)
- SPIRIT (Дух, подсознание, вера, тайное)

ОТВЕТ ДОЛЖЕН БЫТЬ СТРОГО В ВИДЕ JSON:
{
  "IDENTITY": "Ваше Солнце в Скорпионе в 1 доме дает интенсивную личность. Тень: склонность к разрушению и скрытности. Свет: невероятная магнетичность и способность перерождаться из пепла.",
  "MONEY": "Венера в Козероге во 2 доме...",
  ... (описать все 8 сфер)
}
"""

async def synthesize_sphere_descriptions(chart_dict: dict, aspects_dict: list) -> dict:
    """
    Analyzes the natal chart and generates a descriptive text for each of the 8 spheres.
    """
    raw_data = {
        "chart": chart_dict,
        "aspects": aspects_dict
    }
    
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SPHERES_PROMPT},
            {"role": "user", "content": f"Натальная карта:\n{json.dumps(raw_data, ensure_ascii=False)}"}
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error parsing LLM response for sphere descriptions: {e}")
        # Return fallback empty descriptions if parsing fails
        return {sphere: "" for sphere in [
            "IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"
        ]}
