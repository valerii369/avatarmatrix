from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from pgvector.sqlalchemy import Vector

# Layer 1: Event Storage
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    session_id = Column(Integer, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String(64), index=True)  # SESSION_START, IMAGE_HOVER, etc.
    payload_json = Column(JSON)

# Layer 2: Behavioral Features
class SessionFeatures(Base):
    __tablename__ = "session_features"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, unique=True, index=True)
    user_id = Column(Integer, index=True)

    avg_reaction_time = Column(Float)
    first_click_latency = Column(Float) # Time to first response start
    decision_entropy = Column(Float)

    # Narrative/Semantic Metrics
    semantic_shift = Column(Float) # Vector distance between L1 and L5
    narrative_depth = Column(Float) # Complexity/Length ratio
    emotional_volatility = Column(Float) # Variance in emotion vector
    
    archetype_distribution = Column(JSON) # {archetype_id: weight}
    exploration_score = Column(Float)
    hesitation_score = Column(Float)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class UserBehaviorProfileV2(Base):
    __tablename__ = "user_behavior_profile"

    user_id = Column(Integer, primary_key=True)
    avg_decision_speed = Column(Float)
    
    # Narrative Performance
    avg_narrative_depth = Column(Float)
    avg_semantic_shift = Column(Float)
    emotional_stability_index = Column(Float)
    
    archetype_bias_vector = Column(JSON) # Stores distribution/strengths
    
    exploration_index = Column(Float)
    impulsivity_score = Column(Float)
    hesitation_score = Column(Float)
    
    narrative_metrics = Column(JSON) # Extended metrics
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
