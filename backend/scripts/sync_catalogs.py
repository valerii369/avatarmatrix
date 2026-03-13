import asyncio
import os
import sys
from sqlalchemy import select, update, insert

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.models.text_diagnostics import Sphere, Archetype
from app.agents.common import SPHERES, ARCHETYPES

async def sync_spheres(db):
    print("Syncing Spheres...")
    for skey, sdata in SPHERES.items():
        stmt = select(Sphere).where(Sphere.id == sdata['id'])
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        
        if existing:
            # Update existing
            await db.execute(
                update(Sphere)
                .where(Sphere.id == sdata['id'])
                .values(key=sdata['key'], name_ru=sdata['name_ru'])
            )
            print(f"Updated Sphere {sdata['id']}: {sdata['name_ru']}")
        else:
            # Insert missing
            new_sphere = Sphere(
                id=sdata['id'],
                key=sdata['key'],
                name_ru=sdata['name_ru']
            )
            db.add(new_sphere)
            print(f"Inserted Sphere {sdata['id']}: {sdata['name_ru']}")
    await db.commit()

async def sync_archetypes(db):
    print("\nSyncing Archetypes...")
    for arc_id, arc_data in ARCHETYPES.items():
        stmt = select(Archetype).where(Archetype.id == int(arc_id))
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        
        if existing:
            # Update
            await db.execute(
                update(Archetype)
                .where(Archetype.id == int(arc_id))
                .values(name=arc_data['name'])
            )
            print(f"Updated Archetype {arc_id}: {arc_data['name']}")
        else:
            # Insert
            new_arc = Archetype(
                id=int(arc_id),
                name=arc_data['name']
            )
            db.add(new_arc)
            print(f"Inserted Archetype {arc_id}: {arc_data['name']}")
    await db.commit()

async def main():
    async with AsyncSessionLocal() as db:
        await sync_spheres(db)
        await sync_archetypes(db)
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(main())
