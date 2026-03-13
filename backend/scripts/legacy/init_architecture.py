import asyncio
from app.database import engine, Base
# Import all models to ensure they are registered with Base
from app.models.data_architecture import *
from app.models.visual_evolution import *

async def init_tables():
    async with engine.begin() as conn:
        # This will create all tables registered with Base
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables for Data Architecture initialized.")

if __name__ == "__main__":
    asyncio.run(init_tables())
