"""
Manifestation Service v2: Card manifestation from Identity Passport.
Rules:
  - IDENTITY sphere: 1-3 cards (priority: critical > high)
  - Other spheres: 1-2 cards
  - Evolution: when hawkins_peak >= 200, unlock next priority card
  - AI: when ai_score >= threshold from analytics agent
"""
import logging
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.card_progress import CardProgress, CardStatus
from app.models.user import User

logger = logging.getLogger(__name__)

# Max initial cards per sphere
IDENTITY_MAX_CARDS = 3
OTHER_MAX_CARDS = 2


class ManifestationService:
    """
    Manifests archetypes in the user's reality based on vector matching results.
    """

    @staticmethod
    async def manifest_matrix(db: AsyncSession, user_id: int, recommendations: list):
        """
        Processes a list of recommendations and updates CardProgress.
        Enforces per-sphere limits: IDENTITY 1-3, others 1-2.
        """
        if not recommendations:
            return

        # Count currently recommended cards per sphere
        res = await db.execute(
            select(CardProgress).where(
                CardProgress.user_id == user_id,
                CardProgress.status != CardStatus.LOCKED
            )
        )
        existing_active = res.scalars().all()
        active_per_sphere = {}
        for cp in existing_active:
            active_per_sphere[cp.sphere] = active_per_sphere.get(cp.sphere, 0) + 1

        # Fetch ALL existing cards for quick lookup
        all_res = await db.execute(select(CardProgress).where(CardProgress.user_id == user_id))
        existing_cards = {(cp.archetype_id, cp.sphere): cp for cp in all_res.scalars().all()}

        for rec in recommendations:
            archetype_id = rec.archetype_id
            sphere = rec.sphere
            priority = rec.priority
            reason = rec.reason

            # Check sphere limit
            max_cards = IDENTITY_MAX_CARDS if sphere == "IDENTITY" else OTHER_MAX_CARDS
            current_active = active_per_sphere.get(sphere, 0)

            key = (archetype_id, sphere)
            if key in existing_cards:
                cp = existing_cards[key]
                cp.astro_priority = priority
                cp.astro_reason = reason
                if priority in ["critical", "high"] and cp.status == CardStatus.LOCKED and current_active < max_cards:
                    cp.status = CardStatus.RECOMMENDED
                    cp.is_recommended_astro = True
                    cp.recommendation_source = "astro"
                    cp.manifested_at = datetime.datetime.utcnow()
                    active_per_sphere[sphere] = current_active + 1
                db.add(cp)
            else:
                should_recommend = priority in ["critical", "high"] and current_active < max_cards
                status = CardStatus.RECOMMENDED if should_recommend else CardStatus.LOCKED
                cp = CardProgress(
                    user_id=user_id,
                    archetype_id=archetype_id,
                    sphere=sphere,
                    status=status,
                    astro_priority=priority,
                    astro_reason=reason,
                    is_recommended_astro=should_recommend,
                    recommendation_source="astro" if should_recommend else None,
                    manifested_at=datetime.datetime.utcnow() if should_recommend else None
                )
                db.add(cp)
                if should_recommend:
                    active_per_sphere[sphere] = current_active + 1

        await db.flush()

    @staticmethod
    async def sync_with_portrait(db: AsyncSession, user_id: int, portrait_data: dict):
        """
        Semantic Synchronization: Matches passport vector data to archetype cards.
        """
        from app.core.astrology.vector_matcher import match_archetypes_to_spheres
        
        deep_profile = portrait_data.get("deep_profile_data", {})
        spheres_status = deep_profile.get("spheres_status", {})
        
        if not spheres_status:
            return

        matching_input = {"spheres_12": {}}
        for s, data in spheres_status.items():
            matching_input["spheres_12"][s] = {
                "shadow": data.get('shadow', ''),
                "light": data.get('light', ''),
                "insight": data.get('insight', '')
            }

        recommendations = await match_archetypes_to_spheres(db, matching_input, multi_vector=True)
        
        if recommendations:
            await ManifestationService.manifest_matrix(db, user_id, recommendations)
            logger.info(f"Manifestation v2 completed for user {user_id}")
