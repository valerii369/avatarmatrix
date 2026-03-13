import asyncio
import json
import os
import sys

# Add parent path to sys path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "archetype_sphere_matrix.json")

with open(os.path.join(DATA_DIR, "archetypes.json")) as f:
    ARCHETYPES = json.load(f)

with open(os.path.join(DATA_DIR, "spheres.json")) as f:
    SPHERES = json.load(f)

async def generate_description(archetype, sphere):
    prompt = f"""Ты — мастер профайлинга и архитектор смыслов системы AVATAR.
Мне нужно короткое (максимум по 350-400 символов каждое) описание проявления Света и Тени архетипа "{archetype['name']}" ИМЕННО в сфере "{sphere['name_ru']}".

Архетип: {archetype['name']}
Классическая Тень: {archetype['shadow']}
Классический Свет: {archetype['light']}

Сфера: {sphere['name_ru']} — {sphere['main_question']}

ЗАДАЧА:
Напиши, как именно классическая Тень и классический Свет этого архетипа проявляются в этой конкретной сфере жизни.
Не пиши общие слова, пиши конкретно про проявление в этой сфере. Без списков. Без воды. Коротко и глубоко.

Отвечай строго в формате JSON:
{{
  "shadow": "текст про тень архетипа в этой сфере...",
  "light": "текст про свет архетипа в этой сфере..."
}}
"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            data = json.loads(response.choices[0].message.content)
            return {
                "archetype_id": archetype["id"],
                "sphere": sphere["key"],
                "shadow": data.get("shadow", ""),
                "light": data.get("light", "")
            }
        except Exception as e:
            if "Rate limit" in str(e) or "429" in str(e):
                print(f"Rate limit for {archetype['name']} in {sphere['key']}, retrying in 5s...")
                await asyncio.sleep(5)
            else:
                print(f"Error for {archetype['name']} in {sphere['key']}: {e}")
                return None
    return None

async def main():
    matrix = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            matrix = json.load(f)
            
    tasks = []
    
    # Very strict concurrency due to strict limits
    sem = asyncio.Semaphore(2)
    
    async def bound_generate(a, s):
        async with sem:
            await asyncio.sleep(1) # Extra delay to avoid hitting limits
            res = await generate_description(a, s)
            if res:
                print(f"Done: {a['name']} in {s['key']}")
            return res
            
    for a in ARCHETYPES:
        a_id = str(a["id"])
        if a_id not in matrix:
            matrix[a_id] = {}
            
        for s in SPHERES:
            s_key = s["key"]
            if s_key not in matrix[a_id]:
                tasks.append(bound_generate(a, s))
                
    if not tasks:
        print("Everything is already generated.")
        return
        
    print(f"Generating {len(tasks)} missing combinations...")
    results = await asyncio.gather(*tasks)
    
    valid_results = [r for r in results if r]
    
    for r in valid_results:
        a_id = str(r["archetype_id"])
        s_key = r["sphere"]
        matrix[a_id][s_key] = {
            "shadow": r["shadow"],
            "light": r["light"]
        }
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully added {len(valid_results)} combinations.")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
