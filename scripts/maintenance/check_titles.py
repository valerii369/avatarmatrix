import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User
from app.core.economy import get_level_title

async def check_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        print(f"Checking {len(users)} users:")
        for u in users:
            expected = get_level_title(u.evolution_level)
            print(f"User ID: {u.id}, Lvl: {u.evolution_level}, Current Title: '{u.title}', Expected: '{expected}'")
            if u.title != expected:
                print(f"  --> MISMATCH detected for user {u.id}")

if __name__ == "__main__":
    asyncio.run(check_users())
