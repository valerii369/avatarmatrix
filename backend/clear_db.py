import asyncio
import os
import sys
# Path to backend
sys.path.append(os.getcwd())

from sqlalchemy import delete
from app.database import AsyncSessionLocal
from app.models.user_print import UserPrint

async def clear():
    session = AsyncSessionLocal()
    try:
        await session.execute(delete(UserPrint))
        await session.commit()
        print("CLEARED ALL USER PRINTS")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(clear())
