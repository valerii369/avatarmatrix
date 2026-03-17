import asyncio
import os
import sys
sys.path.append(os.getcwd())

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import NatalChart, User
from app.models.user_print import UserPrint

async def check():
    session = AsyncSessionLocal()
    try:
        # Check User onboarding status
        res = await session.execute(select(User).where(User.id == 1))
        user = res.scalar_one_or_none()
        print(f"User 1 onboarding_done: {user.onboarding_done if user else 'NOT FOUND'}")

        # Check NatalChart (L1 Rain)
        res = await session.execute(select(NatalChart).where(NatalChart.user_id == 1))
        chart = res.scalar_one_or_none()
        print(f"NatalChart 1: {'FOUND' if chart else 'NOT FOUND'}")

        # Check UserPrint (L3 Ocean)
        res = await session.execute(select(UserPrint).where(UserPrint.user_id == 1))
        up = res.scalar_one_or_none()
        if up:
            print(f"UserPrint 1: FOUND! Keys: {up.print_data.keys()}")
        else:
            print("UserPrint 1: NOT FOUND (Background synthesis might be running or failed)")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(check())
