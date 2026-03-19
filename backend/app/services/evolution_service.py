import logging
import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user_evolution import UserEvolution
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)

class EvolutionService:
    """
    Service to track user 'touches', thoughts, and session progress.
    Powers the Level 4 (User Evolution) layer.
    """

    @staticmethod
    async def get_or_create(db: AsyncSession, user_id: int) -> UserEvolution:
        res = await db.execute(select(UserEvolution).where(UserEvolution.user_id == user_id))
        evo = res.scalar_one_or_none()
        if not evo:
            evo = UserEvolution(
                user_id=user_id, 
                evolution_data={
                    "touches": [], 
                    "thoughts": [], 
                    "nn_interactions": [], 
                    "session_progress": []
                }
            )
            db.add(evo)
            await db.flush()
        return evo

    @staticmethod
    async def record_touch(
        db: AsyncSession, 
        user_id: int, 
        touch_type: str, 
        payload: Dict[str, Any],
        sentiment: Optional[float] = None
    ):
        """
        Records a single interaction (touch) in the user's evolution timeline.
        """
        evo = await EvolutionService.get_or_create(db, user_id)
        
        if evo.evolution_data is None:
            evo.evolution_data = {"touches": [], "thoughts": [], "nn_interactions": [], "session_progress": []}
            
        touch_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "type": touch_type,
            "payload": payload,
            "sentiment": sentiment
        }
        
        evo.evolution_data["touches"].append(touch_entry)
        evo.update_count_since_vectorization += 1
        
        flag_modified(evo, "evolution_data")
        await db.flush()
        logger.info(f"Touch recorded for user {user_id}: {touch_type}")

    @staticmethod
    async def record_nn_interaction(
        db: AsyncSession, 
        user_id: int, 
        agent_name: str, 
        input_text: str, 
        output_text: str
    ):
        """
        Logs an interaction with a neural network agent.
        """
        evo = await EvolutionService.get_or_create(db, user_id)
        
        interaction = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "agent": agent_name,
            "input": input_text,
            "output": output_text
        }
        
        if "nn_interactions" not in evo.evolution_data:
            evo.evolution_data["nn_interactions"] = []
            
        evo.evolution_data["nn_interactions"].append(interaction)
        evo.update_count_since_vectorization += 1
        
        flag_modified(evo, "evolution_data")
        await db.flush()

    @staticmethod
    async def update_session_progress(
        db: AsyncSession, 
        user_id: int, 
        session_type: str, 
        progress_data: Dict[str, Any]
    ):
        """
        Updates session-related progress (e.g., cards opened, tasks completed).
        """
        evo = await EvolutionService.get_or_create(db, user_id)
        
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "session_type": session_type,
            "data": progress_data
        }
        
        if "session_progress" not in evo.evolution_data:
            evo.evolution_data["session_progress"] = []
            
        evo.evolution_data["session_progress"].append(entry)
        evo.update_count_since_vectorization += 1
        
        flag_modified(evo, "evolution_data")
        await db.flush()

        # Auto-vectorize if enough updates accumulated
        await EvolutionService.vectorize_if_needed(db, user_id)

    @staticmethod
    async def vectorize_if_needed(db: AsyncSession, user_id: int, force: bool = False):
        """Auto-vectorize evolution data after 10 updates for RAG semantic search."""
        evo = await EvolutionService.get_or_create(db, user_id)
        
        if not force and evo.update_count_since_vectorization < 10:
            return
        
        if not evo.evolution_data:
            return

        # Build text representation
        text_parts = []
        touches = evo.evolution_data.get("touches", [])[-20:]
        for t in touches:
            text_parts.append(f"[{t.get('type', '')}] {t.get('payload', {})}")
        
        progress = evo.evolution_data.get("session_progress", [])[-10:]
        for p in progress:
            text_parts.append(f"Session: {p.get('data', {})}")

        if not text_parts:
            return

        text = "\n".join([str(p) for p in text_parts])[:8000]

        try:
            from app.core.astrology.vector_matcher import _get_embedding
            embedding = await _get_embedding(text)
            evo.vector_embedding = embedding
            evo.last_vectorized_at = datetime.datetime.utcnow()
            evo.update_count_since_vectorization = 0
            flag_modified(evo, "vector_embedding")
            await db.flush()
            logger.info(f"Evolution vectorized for user {user_id}")
        except Exception as e:
            logger.error(f"Evolution vectorization failed for user {user_id}: {e}")
