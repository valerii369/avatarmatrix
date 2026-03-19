import logging
import asyncio
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.rro.base import BaseRiver, RiverOutput
from app.core.astrology.llm_engine import synthesize_deep_sphere
from app.rro.passport_service import PassportService

logger = logging.getLogger(__name__)

SPHERES_KEYS = [
    "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
    "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
    "EXPANSION", "STATUS", "VISION", "SPIRIT"
]

class AstroRiver(BaseRiver):
    """
    Astro River (Level 2): Interprets Natal Chart (Rain) into psychological spheres.
    Persists results to Identity Passport via PassportService.
    """
    
    async def flow(self, db: AsyncSession, user_id: int, rain_data: Any) -> RiverOutput:
        """
        Takes NatalChart object and returns deep sphere-by-sphere interpretations.
        """
        logger.info(f"AstroRiver (Deep Loop) flowing for user {user_id}")
        
        try:
            deep_spheres = {}
            
            # 1. Parallel Synthesis (v3.0) for maximum speed
            tasks = [
                synthesize_deep_sphere(
                    sphere,
                    rain_data.planets_json,
                    rain_data.aspects_json
                ) for sphere in SPHERES_KEYS
            ]
            results = await asyncio.gather(*tasks)
            deep_spheres = dict(zip(SPHERES_KEYS, results))
            
            interpretation_data = {"spheres": deep_spheres}
            logic_version = "3.3"

            # 2. Persist to Level 2 Storage (Passport Layer)
            await PassportService.update_channel_data(
                db=db,
                user_id=user_id,
                channel="astrology",
                source="astrologyapi",
                data=interpretation_data
            )
            
            await db.flush()
            logger.info(f"AstroRiver results merged into Passport for user {user_id}")

            return RiverOutput(
                source="astro_river",
                domain="astrology",
                content=interpretation_data,
                metadata={
                    "type": "deep_parallel_persisted",
                    "synthesis_version": logic_version
                }
            )
        except Exception as e:
            logger.error(f"AstroRiver Deep Synthesis failed: {e}")
            return RiverOutput(
                source="astro_river",
                domain="astrology",
                content={},
                metadata={"error": str(e)}
            )
