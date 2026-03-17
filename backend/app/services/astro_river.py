import json
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.base_river import BaseRiver
from app.core.astrology.llm_engine import synthesize_sphere_descriptions
from app.models.natal_chart import NatalChart
from sqlalchemy import select

logger = logging.getLogger(__name__)

class AstroRiver(BaseRiver):
    """
    Astrology River (Level 2): Interprets Natal Chart (Rain) into Sphere Insights.
    """
    
    async def flow(self, db: AsyncSession, user_id: int, rain_data: NatalChart) -> Dict[str, Any]:
        """
        Takes NatalChart model and returns synthesized sphere descriptions.
        """
        logger.info(f"AstroRiver flowing for user {user_id}")
        
        # In this v2 model, synthesize_sphere_descriptions acts as our L2 Astro-Agent
        # We pass the raw chart and aspects (Rain) to it
        chart_dict = rain_data.planets_json
        aspects_dict = rain_data.aspects_json
        
        try:
            interpretation = await synthesize_sphere_descriptions(chart_dict, aspects_dict)
            return {
                "source": "astro_river",
                "content": interpretation,
                "metadata": {"version": "v2_structured"}
            }
        except Exception as e:
            logger.error(f"AstroRiver interpretation failed: {e}")
            return {}
