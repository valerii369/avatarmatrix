import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User
from app.core.economy import get_level_title

async def fix_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        to_save = 0
        for u in users:
            expected = get_level_title(u.evolution_level)
            if u.title != expected:
                print(f"Updating user {u.id}: '{u.title}' -> '{expected}' (Lvl {u.evolution_level})")
                u.title = expected
                db.add(u)
                to_save += 1
        
        if to_save > 0:
            await db.commit()
            print(f"✅ Successfully updated {to_save} users.")
        else:
            print("No title mismatches found.")

if __name__ == "__main__":
    asyncio.run(fix_users())
