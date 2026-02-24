"""
AlignSession: stores data for 6-stage alignment sessions.
Triggered after sync is complete. Uses appropriate Hawkins-level agent.
"""
from typing import Optional
from sqlalchemy import Integer, ForeignKey, String, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class AlignSession(Base, TimestampMixin):
    __tablename__ = "align_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    card_progress_id: Mapped[int] = mapped_column(Integer, ForeignKey("card_progress.id", ondelete="CASCADE"))

    archetype_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sphere: Mapped[str] = mapped_column(String(32), nullable=False)

    # Hawkins tracking: min/peak/exit
    hawkins_entry: Mapped[int] = mapped_column(Integer, default=0)
    hawkins_min: Mapped[int] = mapped_column(Integer, default=0)
    hawkins_peak: Mapped[int] = mapped_column(Integer, default=0)
    hawkins_exit: Mapped[int] = mapped_column(Integer, default=0)

    # Level agent used: 1-10
    agent_level_used: Mapped[int] = mapped_column(Integer, default=1)

    # Full chat history: [{role, content, timestamp}]
    messages_json: Mapped[Optional[list]] = mapped_column(JSONB, default=[])

    # Integration plan generated at end of session
    integration_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Session stages completed (1-6)
    stages_completed: Mapped[int] = mapped_column(Integer, default=0)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pattern analysis from this session
    patterns_identified: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    new_belief: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
