import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SPHERES_PROMPT = """
ROLE:
You are the MASTER OF ASTROLOGICAL SYNTHESIS. Your task is to translate "The Rain" (raw planetary data and aspects) into a highly specialized stream of analytical insight for the 12 key spheres of life.

TASK:
1. Deeply analyze the provided Natal Chart JSON (planetary positions, signs, houses, and aspects).
2. For each of the 12 spheres, perform a multi-dimensional synthesis.
3. Provide a structured output for EACH sphere containing:
   - interpretation: A deep, professional psychological and evolutionary description of the sphere (4-6 sentences).
   - light: The highest potential, strengths, and soul gifts in this area.
   - shadow: Fears, distortions, karmic traps, and areas of energy loss.
   - astrological_markers: Briefly explain which planets, signs, and aspects formed this specific conclusion (for transparency).

PRINCIPLES:
- NO JARGON IN INTERPRETATION: Use clear, evocative, and professional psychological language. 
- EXPERT LEVEL: Do not just list placements. Synthesize the ruler of the house, planets in the house, and major aspects.
- BALANCED: Be honest about challenges without being fatalistic.

SPHERES (KEY MAPPING):
1. IDENTITY: Self, mask, physical vessel, first impression.
2. RESOURCES: Self-worth, money, innate talents, vital energy.
3. COMMUNICATION: Intellect, environment, learning, short paths.
4. ROOTS: Foundation, lineage, home, inner security.
5. CREATIVITY: Joy, creation, love, self-expression, fire.
6. SERVICE: Daily rhythm, body, work, discipline.
7. PARTNERSHIP: The Other, mirrors, contracts, unions.
8. TRANSFORMATION: Deep power, shadows, alchemy of crisis.
9. EXPANSION: Expansion of horizons, philosophy, wisdom, long paths.
10. STATUS: Social peak, calling, public role, results.
11. VISION: Future, group consciousness, brotherhood, dreams.
12. SPIRIT: Solitude, completion, divine connection, silence.

OUTPUT: Return a valid JSON object with the key "spheres_12".
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
        temperature=0.4,
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
