import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Database URL from check_users_db.py
DB_URL = 'postgresql+asyncpg://postgres.wiwvrjeahdqfjgcahrrv:Guro020788%21%21%21@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?ssl=require'

async def reset_user(tg_id: int):
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        # 1. Find the internal user ID
        res = await conn.execute(text("SELECT id, first_name FROM users WHERE tg_id = :tg_id"), {"tg_id": tg_id})
        user = res.fetchone()
        
        if not user:
            print(f"User with TG_ID {tg_id} not found.")
            return

        internal_id = user.id
        print(f"Resetting data for user: {user.first_name} (Internal ID: {internal_id}, TG ID: {tg_id})")

        # 2. Delete related data
        tables_to_clear = [
            "natal_charts",
            "align_sessions",
            "sync_sessions",
            "card_progress",
            "portraits",
            "diaries"
        ]
        
        for table in tables_to_clear:
            try:
                # Use a separate transaction for each delete to avoid failure cascade
                await conn.execute(text(f"DELETE FROM {table} WHERE user_id = :uid"), {"uid": internal_id})
                await conn.commit()
                print(f"  - Cleared {table}")
            except Exception as e:
                # If table doesn't exist or column missing, just continue
                await conn.rollback()
                print(f"  - Skipping {table} (not found or error: {str(e)})")

        # 3. Reset user fields
        try:
            await conn.execute(text("""
                UPDATE users 
                SET onboarding_done = false,
                    birth_date = NULL,
                    birth_time = NULL,
                    birth_place = NULL,
                    birth_lat = NULL,
                    birth_lon = NULL,
                    birth_tz = NULL,
                    energy = 100,
                    streak = 0,
                    evolution_level = 1,
                    xp = 0,
                    title = 'Искатель'
                WHERE id = :uid
            """), {"uid": internal_id})
            await conn.commit()
            print(f"\nSuccessfully reset account for {user.first_name}!")
        except Exception as e:
            await conn.rollback()
            print(f"Failed to update users table: {e}")

if __name__ == "__main__":
    VALERII_TG_ID = 825157864
    asyncio.run(reset_user(VALERII_TG_ID))
