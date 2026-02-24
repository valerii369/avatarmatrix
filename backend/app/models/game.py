from typing import Optional
from sqlalchemy import Integer, ForeignKey, String, Boolean, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date

from app.database import Base
from app.models.base import TimestampMixin


class GameState(Base, TimestampMixin):
    """Extended game state for titles, badges, and unlocks."""
    __tablename__ = "game_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    titles_unlocked: Mapped[Optional[list]] = mapped_column(JSONB, default=[])
    badges_json: Mapped[Optional[list]] = mapped_column(JSONB, default=[])
    current_title: Mapped[str] = mapped_column(String(64), default="Искатель")

    # Daily energy (burns at end of day)
    daily_energy: Mapped[int] = mapped_column(Integer, default=10)
    daily_energy_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class Match(Base, TimestampMixin):
    """Social matching between users with complementary fingerprints."""
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id_1: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user_id_2: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Matched on which sphere
    sphere: Mapped[str] = mapped_column(String(32), nullable=False)

    # Status: pending | accepted | declined | active | closed
    status: Mapped[str] = mapped_column(String(32), default="pending")

    # Chat messages: [{user_id, content, timestamp}]
    chat_json: Mapped[Optional[list]] = mapped_column(JSONB, default=[])

    # Match score (0-100)
    compatibility_score: Mapped[int] = mapped_column(Integer, default=0)
    match_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)


class DailyReflect(Base, TimestampMixin):
    """Daily 3-question reflection — gives +10✦."""
    __tablename__ = "daily_reflect"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    reflect_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Q1: current emotion (maps to Hawkins)
    current_emotion: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hawkins_today: Mapped[int] = mapped_column(Integer, default=0)

    # Q2: yesterday's integration
    integration_done: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # yes/no/partial

    # Q3: today's focus sphere
    focus_sphere: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    energy_awarded: Mapped[int] = mapped_column(Integer, default=0)


class VoiceRecord(Base, TimestampMixin):
    """Voice messages transcribed via Whisper."""
    __tablename__ = "voice_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    audio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)

    # Context: which session or diary entry this belongs to
    session_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    session_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
