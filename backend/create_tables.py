import asyncio
import logging
from app.database import engine, Base
from app.models import * # Import all models to register them with Base.metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables():
    logger.info("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created successfully.")

if __name__ == "__main__":
    asyncio.run(create_tables())
