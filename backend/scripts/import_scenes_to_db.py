import os
import json
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.text_diagnostics import TextScene, Sphere, Archetype

async def import_scenes():
    """Import all JSON scenes from data/generated_scenes into the database."""
    base_dir = "data/generated_scenes"
    if not os.path.exists(base_dir):
        print(f"Directory {base_dir} not found.")
        return

    async with AsyncSessionLocal() as db:
        # Fetch existing spheres/archetypes to map names to IDs
        spheres_res = await db.execute(select(Sphere))
        spheres_map = {s.key: s.id for s in spheres_res.scalars().all()}
        
        archetypes_res = await db.execute(select(Archetype))
        archetypes_map = {a.name: a.id for a in archetypes_res.scalars().all()}

        count = 0
        for sphere_key in os.listdir(base_dir):
            sphere_path = os.path.join(base_dir, sphere_key)
            if not os.path.isdir(sphere_path):
                continue

            sphere_id = spheres_map.get(sphere_key)
            if not sphere_id:
                print(f"Sphere {sphere_key} not found in DB. Skipping.")
                continue

            for filename in os.listdir(sphere_path):
                if not filename.endswith(".json"):
                    continue

                # Filename example: "1_Маг.json" or "0_Шут.json"
                # Extract archetype name: skip digits and underscore, remove .json
                arch_part = filename.replace(".json", "")
                if "_" in arch_part:
                    archetype_name = arch_part.split("_", 1)[1]
                else:
                    archetype_name = arch_part

                file_path = os.path.join(sphere_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        archetype_id = archetypes_map.get(archetype_name)

                        if not archetype_id and archetype_id != 0:
                            print(f"Archetype '{archetype_name}' not found in DB (from {filename}). Skipping.")
                            continue

                        # Map JSON structure to database columns
                        orientation = data.get("immersion_architecture", {}).get("orientation", "")
                        complication = data.get("immersion_architecture", {}).get("complication", "")
                        action_prompt = data.get("transformation_mechanics", {}).get("action_prompt", "")
                        
                        full_text = f"{orientation} {complication}"
                        if action_prompt:
                            full_text += f"\n\n[Системный хук]: {action_prompt}"

                        if not full_text.strip():
                            print(f"Empty text in {file_path}. Skipping.")
                            continue

                        # Check if scene already exists (basic check by text)
                        existing_check = await db.execute(
                            select(TextScene).where(TextScene.scene_text == full_text)
                        )
                        if existing_check.scalar_one_or_none():
                            continue

                        new_scene = TextScene(
                            sphere_id=sphere_id,
                            archetype_id=archetype_id,
                            scene_text=full_text,
                            complexity_score=data.get("complexity", 0.5),
                            ambiguity_score=data.get("ambiguity", 0.5),
                            tension_level=data.get("tension", 0.5),
                            environment_type="Projective Landscape",
                            meta_data=data
                        )
                        db.add(new_scene)
                        count += 1
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")

        await db.commit()
        print(f"Successfully imported {count} scenes.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(import_scenes())
