import asyncio
import json
import os
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.text_diagnostics import TextScene, Sphere, Archetype

async def export():
    async with AsyncSessionLocal() as session:
        # 1. Load mappings
        spheres_res = await session.execute(select(Sphere))
        spheres = {s.id: s.key for s in spheres_res.scalars().all()}
        
        archetypes_res = await session.execute(select(Archetype))
        archetypes = {a.id: a.name for a in archetypes_res.scalars().all()}

        # 2. Fetch all scenes
        res = await session.execute(select(TextScene))
        scenes = res.scalars().all()
        
        print(f"Total scenes to export: {len(scenes)}")

        for s in scenes:
            skey = spheres.get(s.sphere_id)
            aname = archetypes.get(s.archetype_id)
            if not skey or not aname:
                print(f"Warning: Missing mapping for scene ID {s.id}")
                continue
            
            # Directory structure: data/generated_scenes/SPHERE/ID_Name.json
            dir_path = os.path.join("data", "generated_scenes", skey)
            os.makedirs(dir_path, exist_ok=True)
            
            file_name = f"{s.archetype_id}_{aname}.json"
            full_path = os.path.join(dir_path, file_name)
            
            # Meta data is the full JSON object
            data = s.meta_data or {}
            
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Successfully exported {len(scenes)} scenes to data/generated_scenes/")

if __name__ == "__main__":
    asyncio.run(export())
