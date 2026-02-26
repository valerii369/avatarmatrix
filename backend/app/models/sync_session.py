"""
SyncSession: stores data for all 10 phases of the synchronization process.
Each card has one sync session per activation attempt.
"""
from typing import Optional
from sqlalchemy import Integer, ForeignKey, String, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class SyncSession(Base, TimestampMixin):
    __tablename__ = "sync_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    card_progress_id: Mapped[int] = mapped_column(Integer, ForeignKey("card_progress.id", ondelete="CASCADE"))

    archetype_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sphere: Mapped[str] = mapped_column(String(32), nullable=False)

    # Current phase (1-10), 0 = not started
    current_phase: Mapped[int] = mapped_column(Integer, default=0)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # Layer data stored as JSON: { "1": { "ai": "...", "user": "..." }, "2": { "ai": "...", "user": "...", "is_narrowing": true }, ... }
    phase_data: Mapped[Optional[dict]] = mapped_column(JSONB, default={})

    # NEW: Level 3 Knowledge Cell (AvatarCardResult)
    real_picture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    core_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shadow_active: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_anchor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_insight: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Full transcript as a list of {role, content}
    session_transcript: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Legacy/Extended insights (kept for compatibility or extra detail)
    extracted_core_belief: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_shadow_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_body_anchor: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Redundant with body_anchor
    extracted_projection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_avoidance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_dominant_emotion: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extracted_tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Hawkins tracking
    hawkins_score: Mapped[int] = mapped_column(Integer, default=0)
    hawkins_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
