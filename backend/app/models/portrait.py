from typing import Optional
from sqlalchemy import Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class UserPortrait(Base, TimestampMixin):
    """
    Aggregated user portrait used for recommendations.
    One row per user-sphere combination.
    """
    __tablename__ = "user_portrait"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sphere: Mapped[str] = mapped_column(String(32), nullable=False)

    # All card data for this sphere: [{archetype_id, date, extracted, tags}]
    cards_data: Mapped[Optional[list]] = mapped_column(JSONB, default=[])

    # Cross-patterns detected in this sphere
    patterns_json: Mapped[Optional[list]] = mapped_column(JSONB, default=[])

    # Body map: {location: [card_ids], sensation: str}
    body_map_json: Mapped[Optional[dict]] = mapped_column(JSONB, default={})

    # Average Hawkins score for this sphere
    avg_hawkins: Mapped[int] = mapped_column(Integer, default=0)

    # Min Hawkins (determines sphere awareness level)
    min_hawkins: Mapped[int] = mapped_column(Integer, default=0)

    # Hawkins history: [{date, score, archetype_id}]
    hawkins_timeline: Mapped[Optional[list]] = mapped_column(JSONB, default=[])


class Pattern(Base, TimestampMixin):
    """Cross-sphere patterns detected from all sync sessions."""
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    tag: Mapped[str] = mapped_column(String(128), nullable=False)

    # Cards where this pattern appeared: [{archetype_id, sphere, strength}]
    cards_json: Mapped[Optional[list]] = mapped_column(JSONB, default=[])

    # Overall strength 1-10
    strength: Mapped[int] = mapped_column(Integer, default=1)
    occurrences: Mapped[int] = mapped_column(Integer, default=1)


class Connection(Base, TimestampMixin):
    """Connections between cards based on aspects, patterns, or body map."""
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    archetype_id_1: Mapped[int] = mapped_column(Integer, nullable=False)
    sphere_1: Mapped[str] = mapped_column(String(32), nullable=False)
    archetype_id_2: Mapped[int] = mapped_column(Integer, nullable=False)
    sphere_2: Mapped[str] = mapped_column(String(32), nullable=False)

    # Type: horizontal (same sphere), vertical (same archetype), dynamic (pattern-based), aspect
    connection_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    strength: Mapped[int] = mapped_column(Integer, default=1)
