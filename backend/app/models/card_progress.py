"""
CardProgress: tracks user's progress on each of the 176 cards.
Status flow: locked → recommended → in_sync → synced → aligning → aligned
"""
from typing import Optional
from sqlalchemy import Integer, ForeignKey, String, Float, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base
from app.models.base import TimestampMixin


class CardStatus(str, enum.Enum):
    LOCKED = "locked"
    RECOMMENDED = "recommended"
    IN_SYNC = "in_sync"
    SYNCED = "synced"
    ALIGNING = "aligning"
    ALIGNED = "aligned"


class CardProgress(Base, TimestampMixin):
    __tablename__ = "card_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Card identity: archetype 0-21, sphere one of 8
    archetype_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sphere: Mapped[str] = mapped_column(String(32), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(32), default=CardStatus.LOCKED)
    is_recommended_astro: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recommended_portrait: Mapped[bool] = mapped_column(Boolean, default=False)

    # Hawkins tracking
    hawkins_current: Mapped[int] = mapped_column(Integer, default=0)
    hawkins_peak: Mapped[int] = mapped_column(Integer, default=0)
    hawkins_entry: Mapped[int] = mapped_column(Integer, default=0)

    # Rank: 0=Спящий, 1=Пробуждающийся, 2=Осознающий, 3=Мастер, 4=Мудрец, 5=Просветлённый
    rank: Mapped[int] = mapped_column(Integer, default=0)

    # Sessions count
    sync_sessions_count: Mapped[int] = mapped_column(Integer, default=0)
    align_sessions_count: Mapped[int] = mapped_column(Integer, default=0)

    # Astrology priority: critical, high, medium, additional
    astro_priority: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    astro_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
