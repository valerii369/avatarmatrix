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
