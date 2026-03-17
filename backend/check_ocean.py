import asyncio
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import models from our app
import sys
sys.path.append(os.getcwd())
from app.models import UserPortrait, NatalChart, User
from app.rro.ocean.hub import UserPrint  # Wait, check if UserPrint exists in models

async def check():
    url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        # Check UserPrint
        try:
            from app.models import UserPrint as UP
            res = await session.execute(select(UP).where(UP.user_id == 1))
            up = res.scalar_one_or_none()
            if up:
                print(f"FOUND UserPrint: {up.synthesis_json.keys()}")
            else:
                print("UserPrint NOT FOUND for user_id=1")
        except Exception as e:
            print(f"Error checking UserPrint: {e}")

if __name__ == "__main__":
    asyncio.run(check())
