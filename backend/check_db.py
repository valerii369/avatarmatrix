import asyncio
from sqlalchemy import text
from app.database import engine

async def check_db():
    async with engine.connect() as conn:
        # Check avatar_cards structure
        result = await conn.execute(text("SELECT id, archetype_id, sphere FROM avatar_cards LIMIT 10;"))
        rows = result.fetchall()
        print("=== AVATAR_CARDS (first 10) ===")
        for r in rows:
            print(f"  id={r[0]}, archetype_id={r[1]}, sphere={r[2]}")
        
        # Check total count
        count = await conn.execute(text("SELECT COUNT(*) FROM avatar_cards;"))
        print(f"\nTotal avatar_cards: {count.scalar()}")
        
        # Check distinct archetype_id range
        result2 = await conn.execute(text("SELECT MIN(archetype_id), MAX(archetype_id), COUNT(DISTINCT archetype_id) FROM avatar_cards;"))
        row2 = result2.fetchone()
        print(f"archetype_id range: min={row2[0]}, max={row2[1]}, distinct={row2[2]}")
        
        # Check card_progress for user 4
        result3 = await conn.execute(text("SELECT archetype_id, sphere, status, is_recommended_ai, ai_score FROM card_progress WHERE user_id=4 AND is_recommended_ai=true LIMIT 10;"))
        rows3 = result3.fetchall()
        print(f"\n=== RECOMMENDED AI CARDS for user 4 ===")
        for r in rows3:
            print(f"  archetype_id={r[0]}, sphere={r[1]}, status={r[2]}, is_rec_ai={r[3]}, ai_score={r[4]}")
        
        count3 = await conn.execute(text("SELECT COUNT(*) FROM card_progress WHERE user_id=4 AND is_recommended_ai=true;"))
        print(f"\nTotal recommended AI cards for user 4: {count3.scalar()}")

if __name__ == "__main__":
    asyncio.run(check_db())
