import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.rro.base import BaseRiver, RiverOutput
from app.agents.assistant_agent import synthesize_sphere_descriptions

logger = logging.getLogger(__name__)

class AstroRiver(BaseRiver):
    """
    Astro River (Level 2): Interprets Natal Chart (Rain) into psychological spheres.
    """
    
    async def flow(self, db: AsyncSession, user_id: int, rain_data: Any) -> RiverOutput:
        """
        Takes NatalChart object and returns sphere-by-sphere interpretations.
        """
        logger.info(f"AstroRiver flowing for user {user_id}")
        
        try:
            # specialized Agent logic
            sphere_descriptions = await synthesize_sphere_descriptions(rain_data)
            
            return RiverOutput(
                source="astro_river",
                domain="astrology",
                content={"spheres": sphere_descriptions},
                metadata={"source": "natal_chart"}
            )
        except Exception as e:
            logger.error(f"AstroRiver interpretation failed: {e}")
            return RiverOutput(
                source="astro_river",
                domain="astrology",
                content={},
                metadata={"error": str(e)}
            )
