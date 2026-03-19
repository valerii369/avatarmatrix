import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from sqlalchemy import text
from app.database import engine
import app.models # Ensure all models are loaded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLES_TO_TRUNCATE = [
    "natal_charts",
    "river_results",
    "user_prints",
    "card_progress",
    "user_portrait",
    "reflection_sessions",
    "sync_sessions",
    "align_sessions",
    "events",
    "session_features",
    "user_behavior_profile",
    "patterns",
    "connections",
    "user_symbols",
    "user_memory",
    "assistant_sessions",
    "ai_diagnostic_sessions",
    "diary_entries",
    "matches",
    "voice_records",
    "daily_reflects",
    "game_states",
    "user_world_knowledge"
]

async def reset_db():
    logger.info("🚀 Starting robust database reset...")
    
    for table in TABLES_TO_TRUNCATE:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                logger.info(f"✅ Truncated table: {table}")
        except Exception as e:
            logger.warning(f"⚠️ Could not truncate {table} (it might not exist or is already empty): {e}")

    try:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM users CASCADE"))
            await conn.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 1"))
            logger.info("✅ Deleted all users and reset sequence")
    except Exception as e:
        logger.error(f"❌ Error resetting users: {e}")

    logger.info("✨ Database reset completed!")

if __name__ == "__main__":
    asyncio.run(reset_db())
