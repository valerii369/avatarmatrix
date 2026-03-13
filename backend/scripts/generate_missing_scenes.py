import asyncio
import json
import os
import sys
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.future import select

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.models.text_diagnostics import TextScene
from app.agents.common import client, settings, ARCHETYPES, SPHERES
from app.agents.sync_agent import get_embedding

# --- Pydantic Models for Structured Output (Matching generate_projective_scenes.py) ---

class Interpretation(BaseModel):
    object: str
    interpretation_broken: str
    interpretation_beautiful: str
    interpretation_threatening: str

class ImmersionArchitecture(BaseModel):
    orientation: str
    complication: str

class DiagnosticFocus(BaseModel):
    pennebaker_markers: List[str]
    mcadams_markers: List[str]

class TransformationMechanics(BaseModel):
    externalization_question: str
    action_prompt: str

class SceneData(BaseModel):
    scene_name: str
    psychological_foundation: str
    immersion_architecture: ImmersionArchitecture
    projection_dictionary: List[Interpretation]
    diagnostic_focus: DiagnosticFocus
    transformation_mechanics: TransformationMechanics

async def generate_scene_for_pair(sphere: dict, archetype: dict) -> Optional[SceneData]:
    system_prompt = f"""
Ты — старший системный архитектор и эксперт по нарративной психологии AVATAR.
Творчески соединяя Жака Лакана, Карла Юнга, Уильяма Лабова, Генри Мюррея, Джеймса Пеннебейкера, Майкла Уайта и Дэн Макадамса, создай УНИКАЛЬНУЮ проективную текстовую сцену.

СФЕРА В ФОКУСЕ: {sphere['name_ru']} ({sphere['key']})
АРХЕТИП В ФОКУСЕ: {archetype['name']} (Свет: {archetype.get('light', '')}, Тень: {archetype.get('shadow', '')})

ИНСТРУКЦИЯ ПО АРХИТЕКТУРЕ (Лабов + Мюррей):
Orientation: Атмосферное описание стартовой среды. Оно должно быть сюрреалистичным, богатым проекциями и отсылать к архетипу и сфере. Без людей. 2-3 предложения.
Complication: Событие-триггер внутри сцены, создающее давление (Press). 1 предложение.

ИНСТРУКЦИЯ ПО СИМВОЛАМ (Юнг):
Выберите 3 ключевых объекта среды и обоснуйте, что значит для анализа, если пользователь воспримет их как "сломанные", "красивые" или "угрожающие".

СТРОГИЙ ФОРМАТ ВЫВОДА — JSON.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Сгенерируй сцену в формате JSON."}
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "scene_schema", "schema": SceneData.model_json_schema()}},
        )
        return SceneData.model_validate_json(response.choices[0].message.content)
    except Exception as e:
        print(f"Error generating {sphere['name_ru']} + {archetype['name']}: {e}")
        return None

async def main():
    target_sphere_keys = ["EXPANSION", "STATUS", "VISION", "SPIRIT"]
    
    async with AsyncSessionLocal() as db:
        for skey in target_sphere_keys:
            sphere = [s for s in SPHERES.values() if s['key'] == skey][0]
            print(f"--- Processing Sphere: {sphere['name_ru']} (ID {sphere['id']}) ---")
            
            for arc_id, arc in ARCHETYPES.items():
                print(f"Checking Archetype: {arc['name']} ({arc_id})...")
                
                # Check if exists
                stmt = select(TextScene).where(
                    TextScene.sphere_id == sphere['id'],
                    TextScene.archetype_id == int(arc_id)
                )
                res = await db.execute(stmt)
                if res.scalars().first():
                    print("Already exists. Skipping.")
                    continue
                
                print(f"Generating scene for {arc['name']}...")
                scene_data = await generate_scene_for_pair(sphere, arc)
                
                if scene_data:
                    full_text = f"{scene_data.immersion_architecture.orientation} {scene_data.immersion_architecture.complication}"
                    full_text += f"\n\n[Системный хук]: {scene_data.transformation_mechanics.action_prompt}"
                    
                    emb = await get_embedding(full_text)
                    
                    meta_dict = scene_data.model_dump()
                    meta_dict["sphere_id"] = sphere['id']
                    meta_dict["sphere_key"] = skey
                    
                    new_scene = TextScene(
                        sphere_id=sphere['id'],
                        archetype_id=int(arc_id),
                        scene_text=full_text,
                        scene_embedding=emb,
                        environment_type="Projective Landscape",
                        meta_data=meta_dict,
                        is_active=True
                    )
                    db.add(new_scene)
                    await db.commit()
                    print(f"Saved to DB for {arc['name']}!")
                    await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
