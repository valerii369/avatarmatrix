import asyncio
import json
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.text_diagnostics import TextScene, Sphere, Archetype

async def check():
    async with AsyncSessionLocal() as session:
        # 1. Total count
        res = await session.execute(select(func.count(TextScene.id)))
        total = res.scalar()
        print(f"Total scenes in DB: {total}")

        # 2. Check each sphere/archetype
        spheres_res = await session.execute(select(Sphere))
        spheres = spheres_res.scalars().all()
        
        archetypes_res = await session.execute(select(Archetype))
        archetypes = archetypes_res.scalars().all()

        missing = []
        for s in spheres:
            for a in archetypes:
                res = await session.execute(
                    select(TextScene).where(TextScene.sphere_id == s.id, TextScene.archetype_id == a.id)
                )
                if not res.scalar_one_or_none():
                    missing.append(f"{s.key} ({s.name_ru}) + {a.name} (ID: {a.id})")

        if missing:
            print(f"\nMissing {len(missing)} scenes:")
            for m in missing:
                print(f" - {m}")
        else:
            print("\nAll 176 scenes are present in DB!")

if __name__ == "__main__":
    asyncio.run(check())
