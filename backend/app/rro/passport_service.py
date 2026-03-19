import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.identity_passport import IdentityPassport
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)

class PassportService:
    """
    Service to manage the Level 2 Identity Passport.
    Handles aggregation of L1 data and prepares it for L3 simplification.
    """

    @staticmethod
    async def get_or_create(db: AsyncSession, user_id: int) -> IdentityPassport:
        res = await db.execute(select(IdentityPassport).where(IdentityPassport.user_id == user_id))
        passport = res.scalar_one_or_none()
        if not passport:
            passport = IdentityPassport(user_id=user_id, aggregated_data={})
            db.add(passport)
            await db.flush()
        return passport

    @staticmethod
    async def update_channel_data(db: AsyncSession, user_id: int, channel: str, source: str, data: Dict[str, Any]):
        """
        Updates a specific channel (e.g., 'astrology') in the passport.
        """
        passport = await PassportService.get_or_create(db, user_id)
        
        if passport.aggregated_data is None:
            passport.aggregated_data = {}
            
        passport.aggregated_data[channel] = {
            "source": source,
            "data": data
        }
        
        flag_modified(passport, "aggregated_data")
        await db.flush()
        logger.info(f"Passport updated for user {user_id}, channel: {channel}")

    @staticmethod
    async def get_passport_json(db: AsyncSession, user_id: int) -> Optional[Dict[str, Any]]:
        res = await db.execute(select(IdentityPassport).where(IdentityPassport.user_id == user_id))
        passport = res.scalar_one_or_none()
        if passport:
            return passport.aggregated_data
        return None

    @staticmethod
    async def vectorize_passport(db: AsyncSession, user_id: int):
        """Creates/updates vector embedding from passport data for RAG semantic search."""
        import json
        import datetime
        
        passport = await PassportService.get_or_create(db, user_id)
        if not passport.aggregated_data:
            return
        
        # Build text representation for embedding
        text_parts = []
        if passport.simplified_characteristics:
            for k, v in passport.simplified_characteristics.items():
                text_parts.append(f"{k}: {v}")
        if passport.spheres_brief:
            for k, v in passport.spheres_brief.items():
                text_parts.append(f"Сфера {k}: {v}")
        
        if not text_parts:
            return
            
        text = "\n".join(text_parts)
        
        try:
            from app.core.astrology.vector_matcher import _get_embedding
            embedding = await _get_embedding(text[:8000])  # Token limit safety
            passport.vector_embedding = embedding
            passport.last_vectorized_at = datetime.datetime.utcnow()
            flag_modified(passport, "vector_embedding")
            await db.flush()
            logger.info(f"Passport vectorized for user {user_id}")
        except Exception as e:
            logger.error(f"Passport vectorization failed for user {user_id}: {e}")
