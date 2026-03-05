import asyncio
from sqlalchemy import text
from app.database import engine

async def drop_table():
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS ai_diagnostic_sessions CASCADE;"))

if __name__ == "__main__":
    asyncio.run(drop_table())
    print("Table dropped.")
