import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.wiwvrjeahdqfjgcahrrv:Guro020788%21%21%21@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?ssl=require"

async def reset_all_users():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Delete dependent data
        await session.execute(text("DELETE FROM card_progress"))
        await session.execute(text("DELETE FROM natal_charts"))
        await session.execute(text("DELETE FROM daily_reflect"))
        await session.execute(text("DELETE FROM matches"))
        
        # Reset user data
        await session.execute(text("""
            UPDATE users 
            SET onboarding_done = false,
                birth_date = NULL,
                birth_time = NULL,
                birth_place = NULL,
                birth_lat = NULL,
                birth_lon = NULL,
                birth_tz = NULL
        """))
        
        await session.commit()
        print("Database systematically wiped! Ready for clean onboarding.")

if __name__ == "__main__":
    asyncio.run(reset_all_users())
