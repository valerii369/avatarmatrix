import asyncio
from app.database import AsyncSessionLocal
from app.models import User
from app.core.economy import spend_energy, award_energy

async def test():
    async with AsyncSessionLocal() as db:
        user = User(tg_id=123999, first_name="Test", energy=10000, evolution_level=1)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        print(f"Initial energy: {user.energy}")
        
        # Test sync (-35)
        success = await spend_energy(db, user, "sync")
        print(f"Spend Sync success: {success}, current energy: {user.energy}")
        
        # Test alignment (-20)
        success = await spend_energy(db, user, "alignment")
        print(f"Spend Alignment success: {success}, current energy: {user.energy}")
        
        # Test reflection (-15)
        success = await spend_energy(db, user, "reflection")
        print(f"Spend Reflection success: {success}, current energy: {user.energy}")

        # Test deep session (-50)
        success = await spend_energy(db, user, "deep_session")
        print(f"Spend Deep Session success: {success}, current energy: {user.energy}")
        
        # Test free things (should be 0)
        gained = await award_energy(db, user, "daily_login")
        print(f"Gained from daily login: {gained}, current energy: {user.energy}")

if __name__ == "__main__":
    asyncio.run(test())
