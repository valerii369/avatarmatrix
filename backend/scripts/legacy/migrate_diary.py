import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate_diary():
    async with engine.begin() as conn:
        print("Adding missing columns to diary...")
        await conn.execute(text("ALTER TABLE diary ADD COLUMN IF NOT EXISTS hawkins_score INTEGER"))
        await conn.execute(text("ALTER TABLE diary ADD COLUMN IF NOT EXISTS ai_analysis TEXT"))
        print("Migration for diary completed.")

if __name__ == "__main__":
    asyncio.run(migrate_diary())
