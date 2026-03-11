import asyncio
import json
import logging
import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from pydantic import BaseModel, Field

from app.database import AsyncSessionLocal
from app.models.text_diagnostics import TextScene
from app.agents.common import client, settings, ARCHETYPES, SPHERES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models for Structured Output ---

class Interpretation(BaseModel):
    object: str
    interpretation_broken: str
    interpretation_beautiful: str
    interpretation_threatening: str

class ImmersionArchitecture(BaseModel):
    orientation: str
    complication: str

class DiagnosticFocus(BaseModel):
    pennebaker_markers: list[str]
    mcadams_markers: list[str]

class TransformationMechanics(BaseModel):
    externalization_question: str
    action_prompt: str

class SceneData(BaseModel):
    scene_name: str
    psychological_foundation: str
    immersion_architecture: ImmersionArchitecture
    projection_dictionary: list[Interpretation]
    diagnostic_focus: DiagnosticFocus
    transformation_mechanics: TransformationMechanics

# --- Main Generation Logic ---

async def generate_scene_for_pair(sphere_id: int, sphere_key: str, sphere_name: str, archetype: dict) -> SceneData:
    system_prompt = f"""
Ты — старший системный архитектор и эксперт по нарративной психологии AVATAR.
Творчески соединяя Жака Лакана, Карла Юнга, Уильяма Лабова, Генри Мюррея, Джеймса Пеннебейкера, Майкла Уайта и Дэн Макадамса, создай УНИКАЛЬНУЮ проективную текстовую сцену.

СФЕРА В ФОКУСЕ: {sphere_name} ({sphere_key})
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
            model="gpt-4o",  # we need reasoning power
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Сгенерируй сцену в формате JSON."}
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "scene_schema", "schema": SceneData.model_json_schema()}},
            temperature=0.7,
            max_tokens=2000
        )
        return SceneData.model_validate_json(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error generating for {sphere_name} + {archetype['name']}: {e}")
        return None

async def main():
    logger.info("Starting Mass Generation of Projective Scenes...")
    
    # Check what spheres we really have (Keys from DB)
    TARGET_SPHERES = ["IDENTITY", "MONEY"] # Batch 1
    
    async with AsyncSessionLocal() as session:
        for skey in TARGET_SPHERES:
            s_data = [s for s in SPHERES.values() if s['key'] == skey]
            if not s_data:
                logger.warning(f"Sphere {skey} not found.")
                continue
            
            s = s_data[0]
            logger.info(f"--- Processing Sphere: {s['name_ru']} ---")
            
            for arc_id, arc in ARCHETYPES.items():
                logger.info(f"Generating scene for Archetype: {arc['name']} ({arc_id})")
                
                # Check DB if exists
                stmt = select(TextScene).where(
                    TextScene.sphere_id == s['id'],
                    TextScene.archetype_id == int(arc_id)
                )
                res = await session.execute(stmt)
                existing = res.scalars().first()
                if existing:
                    logger.info(f"Scene already exists. Skipping.")
                    continue
                
                scene_data = await generate_scene_for_pair(s['id'], skey, s['name_ru'], arc)
                
                if scene_data:
                    from app.agents.sync_agent import get_embedding
                    
                    # Core scene text combines orientation and complication
                    full_text = f"{scene_data.immersion_architecture.orientation} {scene_data.immersion_architecture.complication}"
                    # Add transformation mechanics prompt as a hook
                    full_text += f"\n\n[Системный хук]: {scene_data.transformation_mechanics.action_prompt}"
                    
                    emb = await get_embedding(full_text)
                    
                    meta_dict = scene_data.model_dump()
                    meta_dict["sphere_id"] = s['id']
                    meta_dict["sphere_key"] = skey
                    
                    new_scene = TextScene(
                        sphere_id=s['id'],
                        archetype_id=int(arc_id),
                        scene_text=full_text,
                        scene_embedding=emb,
                        environment_type="Projective Landscape",
                        meta_data=meta_dict,
                        is_active=True
                    )
                    session.add(new_scene)
                    await session.commit()
                    logger.info("Saved to DB!")

if __name__ == "__main__":
    asyncio.run(main())
