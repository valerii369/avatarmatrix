from typing import Optional
from sqlalchemy import Integer, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class DiaryEntry(Base, TimestampMixin):
    __tablename__ = "diary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    align_session_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("align_sessions.id", ondelete="SET NULL"), nullable=True
    )

    archetype_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sphere: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Content text or transcribed voice
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voice_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    voice_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Analysis results
    hawkins_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # AI Insight / Summary

    # Integration plan
    integration_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    integration_done: Mapped[bool] = mapped_column(Boolean, default=False)
    integration_done_partially: Mapped[bool] = mapped_column(Boolean, default=False)

    # Entry type: session_result | manual | voice | reflection
    entry_type: Mapped[str] = mapped_column(String(32), default="session_result")
