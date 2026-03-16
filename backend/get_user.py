import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User

async def run():
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(User).order_by(User.id.desc()).limit(1))
        u = res.scalar()
        if u:
            print(u.id)
        else:
            print("No users found")

if __name__ == "__main__":
    asyncio.run(run())
