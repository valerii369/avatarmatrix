import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.card_progress import CardProgress, CardStatus
from app.models.user import User

logger = logging.getLogger(__name__)

class ManifestationService:
    """
    Manifestation Service: Responsible for 'manifesting' archetypes in the user's reality 
    based on the instructions from the Ocean Hub (User Print).
    """

    @staticmethod
    async def manifest_matrix(db: AsyncSession, user_id: int, recommendations: list):
        """
        Processes a list of recommendations and updates CardProgress.
        Transactional commit is managed AT THE HUB LEVEL.
        """
        if not recommendations:
            return

        # Fetch current cards
        res = await db.execute(select(CardProgress).where(CardProgress.user_id == user_id))
        existing_cards = {(cp.archetype_id, cp.sphere): cp for cp in res.scalars().all()}

        for rec in recommendations:
            archetype_id = rec.archetype_id
            sphere = rec.sphere
            priority = rec.priority
            reason = rec.reason

            key = (archetype_id, sphere)
            if key in existing_cards:
                cp = existing_cards[key]
                cp.astro_priority = priority
                cp.astro_reason = reason
                if priority in ["critical", "high"] and cp.status == CardStatus.LOCKED:
                    cp.status = CardStatus.RECOMMENDED
                db.add(cp)
            else:
                status = CardStatus.RECOMMENDED if priority in ["critical", "high"] else CardStatus.LOCKED
                cp = CardProgress(
                    user_id=user_id,
                    archetype_id=archetype_id,
                    sphere=sphere,
                    status=status,
                    astro_priority=priority,
                    astro_reason=reason
                )
                db.add(cp)
        
        # No commit here! Manifestation is part of the larger Ocean transaction.
        await db.flush()

    @staticmethod
    async def sync_with_portrait(db: AsyncSession, user_id: int, portrait_data: dict):
        """
        Semantic Synchronization (Senior v3.1): 
        Now supports multi-vector matching and atomic flushing.
        """
        from app.core.astrology.vector_matcher import match_archetypes_to_spheres
        
        deep_profile = portrait_data.get("deep_profile_data", {})
        spheres_status = deep_profile.get("spheres_status", {})
        
        if not spheres_status:
            return

        # 1. Prepare multi-vector inputs for parallel matching
        # (Detailed Shadow/Light/Insight separation logic)
        matching_input = {"spheres_12": {}}
        for s, data in spheres_status.items():
            matching_input["spheres_12"][s] = {
                "shadow": data.get('shadow', ''),
                "light": data.get('light', ''),
                "insight": data.get('insight', '')
            }

        # 2. Parallel Vector Search
        recommendations = await match_archetypes_to_spheres(db, matching_input, multi_vector=True)
        
        # 3. Manifest (Flush only)
        if recommendations:
            await ManifestationService.manifest_matrix(db, user_id, recommendations)
            logger.info(f"Manifestation (flushed) for user {user_id}")


