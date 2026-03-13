import asyncio
import json
import os
import sys
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.common import client, settings, ARCHETYPES, SPHERES

# --- Pydantic Models for Structured Output ---

class LevelConsciousness(BaseModel):
    level_name: str
    consciousness: str
    thinking: str
    body: str
    relations: str
    speech: str
    quantum_shift: str
    speech_markers: List[str]

class SphereDescription(BaseModel):
    shadow: str
    light: str
    description: str
    core_shadow: str
    core_light: str
    core_description: str
    levels: Dict[str, LevelConsciousness]
    agent_question: str
    linked_cards: List[str] = Field(default_factory=list)
    xp_reward: int = 50

# --- Prompt Construction ---

def build_generation_prompt(archetype: dict, sphere: dict) -> str:
    return f"""
Ты — эксперт высшего уровня по аналитической психологии, Таро, психосоматике и спиральной динамике.
Ты работаешь над системой AVATAR. Твоя задача: сгенерировать глубокий, структурный и психологически точный анализ связки Архетипа и Сферы Жизни.

АРХЕТИП: {archetype['name']}
СВЕТ: {archetype.get('light', '')}
ТЕНЬ: {archetype.get('shadow', '')}

СФЕРА ЖИЗНИ: {sphere['name_ru']}
ГЛАВНЫЙ ВОПРОС СФЕРЫ: {sphere['main_question']}

ИНСТРУКЦИИ:
1. Опиши Тень, Свет и общее Описание (description) этой связки.
2. Сгенерируй детальные маркеры для уровней сознания (Шкала Хокинса): 20, 50, 100, 175, 200, 310, 400, 500, 600, 700.
3. Для каждого уровня опиши: Состояние сознания, Мышление, Телесные реакции (психосоматика), Отношения, Характер речи, Квантовый скачок (как перейти выше).
4. Добавь 7 ключевых слов-маркеров (speech_markers) для каждого уровня.
5. Сформулируй 1 точный вопрос (agent_question) от ИИ-наставника, который «вскроет» текущее состояние пользователя в этой связке.

Язык: РУССКИЙ.
Формат: Строго JSON по схеме SphereDescription.
"""

async def generate_sphere_data(archetype: dict, sphere: dict) -> Optional[SphereDescription]:
    prompt = build_generation_prompt(archetype, sphere)
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Ты AI-психолог, генерирующий экспертные данные для системы AVATAR."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "sphere_description", "schema": SphereDescription.model_json_schema()}},
        )
        return SphereDescription.model_validate_json(response.choices[0].message.content)
    except Exception as e:
        print(f"Error generating {archetype['name']} + {sphere['key']}: {e}")
        return None

async def main():
    matrix_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "archetype_sphere_matrix.json")
    
    with open(matrix_path, "r", encoding="utf-8") as f:
        matrix = json.load(f)
    
    missing_spheres = ["COMMUNICATION", "CREATIVITY", "TRANSFORMATION", "VISION"]
    
    for arc_id_str, arc_data in ARCHETYPES.items():
        if arc_id_str not in matrix:
            matrix[arc_id_str] = {
                "_meta": {
                    "archetype_id": int(arc_id_str),
                    "archetype_name": arc_data["name"],
                    "archetype_name_en": arc_data.get("name_en", "")
                }
            }
        
        for skey in missing_spheres:
            if skey in matrix[arc_id_str]:
                print(f"Skipping {arc_data['name']} + {skey} (already exists)")
                continue
            
            print(f"Generating data for {arc_data['name']} + {skey}...")
            sphere = [s for s in SPHERES.values() if s['key'] == skey][0]
            
            data = await generate_sphere_data(arc_data, sphere)
            if data:
                matrix[arc_id_str][skey] = data.model_dump()
                # Save after each successful generation to prevent data loss
                with open(matrix_path, "w", encoding="utf-8") as f:
                    json.dump(matrix, f, ensure_ascii=False, indent=2)
                print(f"Saved {arc_data['name']} + {skey}!")
                # Brief sleep to respect rate limits
                await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
