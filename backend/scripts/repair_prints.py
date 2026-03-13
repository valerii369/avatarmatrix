import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import from the app
from app.database import AsyncSessionLocal
from app.models.natal_chart import NatalChart
from app.models.user_print import UserPrint
from app.core.user_print_manager import UserPrintManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def repair_prints():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import text
        # Optional: Specific wipe for user 2 to ensure clean restart
        await session.execute(text("DELETE FROM user_prints WHERE user_id = 2"))
        await session.commit()

        # 1. Find all users with Natal Charts
        res = await session.execute(select(NatalChart))
        charts = res.scalars().all()
        
        for chart in charts:
            # 2. Check if UserPrint exists
            print_res = await session.execute(select(UserPrint).where(UserPrint.user_id == chart.user_id))
            up = print_res.scalar_one_or_none()
            
            # If no print, or if it's "empty" (no spheres OR no identity)
            is_invalid = not up or not up.print_data or not up.print_data.get("spheres") or not up.print_data.get("identity")
            
            if is_invalid:
                logger.info(f"Repairing/Resetting UserPrint for user {chart.user_id}...")
                if chart.sphere_descriptions_json:
                    await UserPrintManager.initialize_from_astro(
                        session, 
                        chart.user_id, 
                        chart.sphere_descriptions_json
                    )
                    # Note: initialize_from_astro commits internally
                else:
                    logger.warning(f"No sphere descriptions in NatalChart for user {chart.user_id}")
            else:
                logger.info(f"UserPrint for user {chart.user_id} is already populated.")

if __name__ == "__main__":
    asyncio.run(repair_prints())
