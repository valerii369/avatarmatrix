import asyncio
import json
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Assuming these are available from the backend app context
from app.database import AsyncSessionLocal
from app.models.text_diagnostics import TextScene, Sphere, Archetype

async def export_scenes():
    async with AsyncSessionLocal() as session:
        # Note: Depending on relationships, we might need a join if not configured.
        # So let's fall back to joining explicitly if relationships aren't loaded.
        
        stmt = select(TextScene, Sphere, Archetype).join(
            Sphere, TextScene.sphere_id == Sphere.id, isouter=True
        ).join(
            Archetype, TextScene.archetype_id == Archetype.id, isouter=True
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        data = []
        for scene, sphere, archetype in rows:
            data.append({
                "id": scene.id,
                "sphere_id": scene.sphere_id,
                "sphere_key": sphere.key if sphere else None,
                "archetype_id": scene.archetype_id,
                "archetype_name": archetype.name if archetype else None,
                "scene_text": scene.scene_text,
                "complexity_score": scene.complexity_score,
                "ambiguity_score": scene.ambiguity_score,
                "tension_level": scene.tension_level,
                "environment_type": scene.environment_type,
                "version": scene.version,
                "is_active": scene.is_active
            })
            
    with open("data/text_scenes_export.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"Exported {len(data)} scenes to data/text_scenes_export.json")

if __name__ == "__main__":
    asyncio.run(export_scenes())
