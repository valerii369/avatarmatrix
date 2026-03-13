import asyncio
from app.database import AsyncSessionLocal
from app.routers.profile import reset_profile_by_tg
from app.models import User
from sqlalchemy import select

async def test_reset():
    async with AsyncSessionLocal() as session:
        # Find any user
        res = await session.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
            print("No users found")
            return
        print(f"Testing reset for user tg_id: {user.tg_id}")
        
        try:
            res = await reset_profile_by_tg(tg_id=user.tg_id, db=session)
            print("Success:", res)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_reset())
