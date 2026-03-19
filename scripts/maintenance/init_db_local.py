import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.database import init_db
import app.models # Ensure all models are loaded

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()

if __name__ == "__main__":
    asyncio.run(main())
