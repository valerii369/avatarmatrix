from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from pgvector.sqlalchemy import Vector

# Catalog Tables
class Sphere(Base):
    __tablename__ = "spheres"
    id = Column(Integer, primary_key=True)
    key = Column(String(32), unique=True, index=True)
    name_ru = Column(String(64))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Archetype(Base):
    __tablename__ = "archetypes"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Stimulus Library
class TextScene(Base):
    __tablename__ = "text_scenes"

    id = Column(Integer, primary_key=True)
    sphere_id = Column(Integer, ForeignKey("spheres.id"), index=True)
    archetype_id = Column(Integer, ForeignKey("archetypes.id"), index=True)
    scene_text = Column(Text)
    scene_embedding = Column(Vector(1536)) # OpenAI embeddings size

    complexity_score = Column(Float, default=0.5)
    ambiguity_score = Column(Float, default=0.5)
    tension_level = Column(Float, default=0.5)
    environment_type = Column(String(64))

    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Scene Interaction logging
class SceneInteraction(Base):
    __tablename__ = "scene_interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    session_id = Column(Integer, index=True)
    scene_id = Column(Integer, ForeignKey("text_scenes.id"), index=True)
    layer_index = Column(Integer) # 1-5

    reading_time = Column(Float)
    reaction_time = Column(Float)
    pause_before_response = Column(Float)

    response_text = Column(Text)
    response_embedding = Column(Vector(1536))
    response_length = Column(Integer)
    extracted_features = Column(JSON) # Structured features (actions, emotions, patterns)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Performance Metrics
class SceneStats(Base):
    __tablename__ = "scene_stats"

    scene_id = Column(Integer, ForeignKey("text_scenes.id"), primary_key=True)
    times_shown = Column(Integer, default=0)
    times_selected = Column(Integer, default=0) # If choosing between scenes

    avg_reading_time = Column(Float, default=0.0)
    avg_response_length = Column(Float, default=0.0)
    
    response_entropy = Column(Float, default=0.0)
    diagnostic_power_score = Column(Float, default=1.0)

# Scene Sets for a session
class SceneSet(Base):
    __tablename__ = "scene_sets"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SceneSetItem(Base):
    __tablename__ = "scene_set_items"
    id = Column(Integer, primary_key=True)
    scene_set_id = Column(Integer, ForeignKey("scene_sets.id"))
    scene_id = Column(Integer, ForeignKey("text_scenes.id"))
    position = Column(Integer) # Order in session (Layer 1-5)
