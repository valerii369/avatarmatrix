from typing import List, Dict, Any
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.data_architecture import Event, SessionFeatures, UserBehaviorProfileV2
from app.models.text_diagnostics import SceneInteraction, Sphere, Archetype

class FeatureExtractor:
    """
    Extracts high-level behavioral features from raw event sequences and narrative transcripts.
    """

    @staticmethod
    async def process_sync_session(db: AsyncSession, session_id: int, user_id: int):
        """
        Processes textual diagnostic data from a sync session.
        Merges timing metrics with structured narrative features.
        """
        # 1. Fetch interactions
        result = await db.execute(
            select(SceneInteraction).where(SceneInteraction.session_id == session_id).order_by(SceneInteraction.layer_index)
        )
        interactions = result.scalars().all()
        if not interactions:
            return

        # 2. Extract Narrative & Semantic Features
        # - Semantic Shift: Distance between Layer 1 and Layer 5
        semantic_shift = 0.0
        if len(interactions) >= 2:
            l1 = next((i for i in interactions if i.layer_index == 1), None)
            l5 = next((i for i in interactions if i.layer_index == 5), None)
            if l1 and l5 and l1.response_embedding is not None and l5.response_embedding is not None:
                v1 = np.array(l1.response_embedding)
                v5 = np.array(l5.response_embedding)
                semantic_shift = float(np.linalg.norm(v1 - v5))

        # - Timing & Depth
        avg_reading_time = np.mean([i.reading_time for i in interactions if i.reading_time]) if interactions else 0
        avg_resp_len = np.mean([len(i.response_text) for i in interactions]) if interactions else 0
        narrative_depth = float(avg_resp_len / 500) # Simple normalization
        
        # - Emotional Volatility (from extracted_features)
        emotion_vectors = [i.extracted_features.get("emotion_vector", {}) for i in interactions if i.extracted_features]
        volatility = 0.0
        if emotion_vectors:
            # Variance across all emotion keys
            all_vals = []
            for ev in emotion_vectors:
                all_vals.extend(ev.values())
            if all_vals:
                volatility = float(np.var(all_vals))

        # 3. Decision Metrics (Hesitation / Entropy)
        # Higher reading time + mid-length responses = higher reflection
        # Very short responses + high speed = impulsivity
        hesitation_score = float(np.clip(avg_reading_time / 15.0, 0, 1)) # Normalize to 15s

        # 4. Update Global User Profile
        profile_res = await db.execute(select(UserBehaviorProfileV2).where(UserBehaviorProfileV2.user_id == user_id))
        profile = profile_res.scalar_one_or_none()
        
        if not profile:
            profile = UserBehaviorProfileV2(user_id=user_id)
            db.add(profile)
            await db.flush()

        alpha = 0.25 # Smoothing factor
        profile.avg_semantic_shift = (1-alpha)*(profile.avg_semantic_shift or 0.0) + alpha*semantic_shift
        profile.avg_narrative_depth = (1-alpha)*(profile.avg_narrative_depth or 0.0) + alpha*narrative_depth
        profile.emotional_stability_index = (1-alpha)*(profile.emotional_stability_index or 0.5) + alpha*(1.0 - volatility)
        profile.hesitation_score = (1-alpha)*(profile.hesitation_score or 0.0) + alpha*hesitation_score
        profile.avg_decision_speed = (1-alpha)*(profile.avg_decision_speed or 0.5) + alpha*(1.0 - hesitation_score)

        # 5. Store Session Summary
        session_feat = SessionFeatures(
            session_id=session_id,
            user_id=user_id,
            avg_reaction_time=avg_reading_time,
            semantic_shift=semantic_shift,
            narrative_depth=narrative_depth,
            emotional_volatility=volatility,
            hesitation_score=hesitation_score
        )
        db.add(session_feat)
        
        await db.commit()

    @staticmethod
    async def process_session(db: AsyncSession, session_id: int, user_id: int):
        """
        Legacy method for image-based sessions. 
        Deprecated in favor of process_sync_session.
        """
        pass
