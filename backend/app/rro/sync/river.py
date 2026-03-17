import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.rro.base import BaseRiver, RiverOutput
from app.agents.analytic_agent import run_mirror_analysis

logger = logging.getLogger(__name__)

class SyncRiver(BaseRiver):
    """
    Sync River (Level 2): Interprets Synchronization Session (Rain) into psychological insights.
    """
    
    async def flow(self, db: AsyncSession, user_id: int, rain_data: Dict[str, Any]) -> RiverOutput:
        """
        Takes raw session data (transcript, metrics) and returns analyzed context.
        """
        logger.info(f"SyncRiver flowing for user {user_id}")
        
        session_id = rain_data.get("session_id")
        transcript = rain_data.get("transcript", [])
        phase_data = rain_data.get("phase_data", {})
        archetype_id = rain_data.get("archetype_id")
        sphere = rain_data.get("sphere")
        
        try:
            analysis = await run_mirror_analysis(
                archetype_id=archetype_id,
                sphere=sphere,
                session_transcript=transcript,
                phase_data=phase_data,
                db=db
            )
            
            return RiverOutput(
                source="sync_river",
                domain="psychology",
                content={
                    "sphere": sphere,
                    "archetype_id": archetype_id,
                    "analysis": analysis
                },
                metadata={"session_id": session_id}
            )
        except Exception as e:
            logger.error(f"SyncRiver interpretation failed: {e}")
            return RiverOutput(
                source="sync_river",
                domain="psychology",
                content={},
                metadata={"error": str(e)}
            )
