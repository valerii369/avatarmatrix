import asyncio
import os
import sys
from sqlalchemy import select, func

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.models.text_diagnostics import TextScene
from app.agents.common import SPHERES

async def main():
    async with AsyncSessionLocal() as session:
        stmt = select(TextScene.sphere_id, func.count(TextScene.id)).group_by(TextScene.sphere_id)
        res = await session.execute(stmt)
        counts = res.all()
        
        print("\nScene counts per Sphere ID:")
        for sid, count in counts:
            sphere_name = "Unknown"
            for s in SPHERES.values():
                if s['id'] == sid:
                    sphere_name = s['name_ru']
                    break
            print(f"ID {sid} ({sphere_name}): {count}")
        
        total = sum(c[1] for c in counts)
        print(f"\nTotal scenes: {total}\n")

if __name__ == "__main__":
    asyncio.run(main())
