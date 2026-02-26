import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def run():
    engine = create_async_engine('postgresql+asyncpg://postgres.wiwvrjeahdqfjgcahrrv:Guro020788%21%21%21@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?ssl=require')
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT * FROM users WHERE tg_id = 825157864'))
        user = res.fetchone()
        if user:
            print(f"FOUND: ID={user.id}, tg_id={user.tg_id}, onboarding_done={user.onboarding_done}, birth_date={user.birth_date}")
        else:
            print("NOT FOUND in database")

if __name__ == "__main__":
    asyncio.run(run())
