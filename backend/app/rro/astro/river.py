import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.rro.base import BaseRiver, RiverOutput
from app.core.astrology.llm_engine import synthesize_deep_sphere

logger = logging.getLogger(__name__)

SPHERES_KEYS = [
    "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
    "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
    "EXPANSION", "STATUS", "VISION", "SPIRIT"
]

class AstroRiver(BaseRiver):
    """
    Astro River (Level 2): Interprets Natal Chart (Rain) into psychological spheres.
    Sequential version (v2.2) for maximum depth.
    """
    
    async def flow(self, db: AsyncSession, user_id: int, rain_data: Any) -> RiverOutput:
        """
        Takes NatalChart object and returns deep sphere-by-sphere interpretations.
        """
        logger.info(f"AstroRiver (Deep Loop) flowing for user {user_id}")
        
        try:
            deep_spheres = {}
            
            # Sequential Loop for maximum depth per sphere
            for sphere in SPHERES_KEYS:
                logger.debug(f"Synthesizing deep data for sphere: {sphere}")
                sphere_data = await synthesize_deep_sphere(
                    sphere,
                    rain_data.planets_json,
                    rain_data.aspects_json
                )
                deep_spheres[sphere] = sphere_data
            
            return RiverOutput(
                source="astro_river",
                domain="astrology",
                content={"spheres": deep_spheres},
                metadata={
                    "type": "deep_sequential",
                    "synthesis_version": "2.2"
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
