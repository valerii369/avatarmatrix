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

    # Phase data stored as JSON for each completed phase
    # phase_data[phase_number] = {prompt, user_response, ai_analysis, ...}
    phase_data: Mapped[Optional[dict]] = mapped_column(JSONB, default={})

    # Extracted insights at completion
    extracted_core_belief: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_shadow_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_body_anchor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_projection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_avoidance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_dominant_emotion: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extracted_tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Hawkins score at phase 10
    hawkins_score: Mapped[int] = mapped_column(Integer, default=0)
    hawkins_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
