import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate():
    async with engine.begin() as conn:
        print("Adding missing columns to sync_sessions...")
        await conn.execute(text("ALTER TABLE sync_sessions ADD COLUMN IF NOT EXISTS real_picture TEXT"))
        await conn.execute(text("ALTER TABLE sync_sessions ADD COLUMN IF NOT EXISTS core_pattern TEXT"))
        await conn.execute(text("ALTER TABLE sync_sessions ADD COLUMN IF NOT EXISTS shadow_active TEXT"))
        await conn.execute(text("ALTER TABLE sync_sessions ADD COLUMN IF NOT EXISTS body_anchor TEXT"))
        await conn.execute(text("ALTER TABLE sync_sessions ADD COLUMN IF NOT EXISTS first_insight TEXT"))
        await conn.execute(text("ALTER TABLE sync_sessions ADD COLUMN IF NOT EXISTS session_transcript JSONB"))
        print("Migration completed.")

if __name__ == "__main__":
    asyncio.run(migrate())
