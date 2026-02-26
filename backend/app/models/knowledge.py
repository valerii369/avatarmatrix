from typing import Optional, List
from sqlalchemy import Integer, ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database import Base
from app.models.base import TimestampMixin


class SphereKnowledge(Base, TimestampMixin):
    """
    Level 2 Knowledge Cell: Aggregated insights for a specific sphere.
    """
    __tablename__ = "sphere_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sphere: Mapped[str] = mapped_column(String(32), nullable=False)

    sphere_picture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # общая картина по сфере
    sphere_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # доминирующий паттерн в сфере
    sphere_hawkins: Mapped[int] = mapped_column(Integer, default=0)            # средневзвешенный уровень по сфере
    
    cards_completed: Mapped[Optional[list]] = mapped_column(JSONB, default=[]) # список пройденных карточек archetypes

    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserWorldKnowledge(Base, TimestampMixin):
    """
    Level 1 Knowledge Cell: Aggregated insights for the entire user's world.
    """
    __tablename__ = "user_world_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)

    overall_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # сквозной паттерн через все сферы
    dominant_shadow: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # доминирующая тень в целом
    hawkins_baseline: Mapped[int] = mapped_column(Integer, default=0)              # базовый уровень сознания
    
    spheres_completed: Mapped[Optional[list]] = mapped_column(JSONB, default=[])   # список пройденных сфер

    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
