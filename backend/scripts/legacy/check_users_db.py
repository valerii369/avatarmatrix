import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def run():
    engine = create_async_engine('postgresql+asyncpg://postgres.wiwvrjeahdqfjgcahrrv:Guro020788%21%21%21@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?ssl=require')
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT id, tg_id, first_name, onboarding_done, birth_date FROM users'))
        rows = res.fetchall()
        for row in rows:
            print(f"ID: {row.id}, TG_ID: {row.tg_id}, Name: {row.first_name}, Onboarding: {row.onboarding_done}, Birth: {row.birth_date}")

if __name__ == "__main__":
    asyncio.run(run())
