from typing import Optional
from sqlalchemy import Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class NatalChart(Base, TimestampMixin):
    __tablename__ = "natal_charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Raw positions (JSON): {planet: {sign, house, degree, retrograde}}
    planets_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Aspects (JSON): [{planet1, planet2, type, orb}]
    aspects_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Recommended cards from astrology calculation
    # [{archetype_id, sphere, priority, reason}]
    # REMOVED: recommended_cards_json (Now handled in Level 3 Manifestation)

    # Ascendant sign and ruler
    ascendant_sign: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ascendant_ruler: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Stelliums detected
    stelliums_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Birth location name for reference
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # REMOVED: sphere_descriptions_json (Now handled in Level 2 River)

    # NEW: Advanced Technical Markers (Senior +++)
    moon_phase: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    technical_summary_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # NEW: Level 1 API Raw Data (astrologyapi.com)
    api_raw_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
