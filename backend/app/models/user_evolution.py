from typing import Optional
from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.models.base import TimestampMixin

class UserEvolution(Base, TimestampMixin):
    """
    User Evolution Layer: Tracks user interactions, thoughts, and progress.
    Separated from the Identity Passport to maintain a dynamic record of touches.
    """
    __tablename__ = "user_evolutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)

    # Evolution data: {touches: [], thoughts: [], nn_interactions: [], session_progress: []}
    # Touches: [{timestamp, type, target_id, sentiment, complexity}]
    # Thoughts: [{timestamp, content, vector_id}]
    evolution_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Vector representation of the user's current 'state' or 'narrative flow'
    vector_embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1536), nullable=True)

    # Smart logic metadata (for vectorization triggers)
    last_vectorized_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    update_count_since_vectorization: Mapped[int] = mapped_column(Integer, default=0)
