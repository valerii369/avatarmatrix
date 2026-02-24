from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, String, Date, Time, Float, Integer, Boolean, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    tg_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Birth data
    birth_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    birth_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)  # "14:30"
    birth_place: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    birth_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    birth_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    birth_tz: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Game state
    energy: Mapped[int] = mapped_column(Integer, default=100)  # ✦
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    evolution_level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(64), default="Искатель")

    # Status
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str] = mapped_column(String(8), default="ru")
