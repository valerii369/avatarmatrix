import asyncio
import json
import os
import sys
from sqlalchemy import select

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        
        # 3. Export to single JSON file for portability
        export_path = os.path.join("data", "text_scenes_export.json")
        full_output = []
        for s in scenes:
            skey = spheres.get(s.sphere_id, "UNKNOWN")
            full_output.append({
                "id": s.id,
                "sphere_id": s.sphere_id,
                "sphere_key": skey,
                "archetype_id": s.archetype_id,
                "scene_text": s.scene_text,
                "complexity_score": s.complexity_score,
                "ambiguity_score": s.ambiguity_score,
                "tension_level": s.tension_level,
                "environment_type": s.environment_type,
                "version": s.version,
                "is_active": s.is_active,
                "meta_data": s.meta_data
            })
        
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(full_output, f, ensure_ascii=False, indent=2)

        print(f"Successfully exported {len(scenes)} scenes to data/generated_scenes/ and {export_path}")

if __name__ == "__main__":
    asyncio.run(export())
