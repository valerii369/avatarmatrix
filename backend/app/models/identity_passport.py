from typing import Optional
from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.models.base import TimestampMixin

class IdentityPassport(Base, TimestampMixin):
    """
    Level 2: Identity Passport (The Core Identity).
    Aggregates data from multiple L1 channels (Astro, etc.) into a structured JSON.
    Includes a vector embedding for semantic search/matching.
    """
    __tablename__ = "identity_passports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)

    # Aggregated profile data with attribution:
    # {
    #   "astrology": { "source": "astrologyapi", "data": {...} },
    #   "human_design": { "source": "external_api", "data": {...} },
    #   ...
    # }
    aggregated_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Vector representation of the identity for smart matching
    vector_embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1536), nullable=True)

    # Simplified L3 characteristics for quick access:
    # { "characteristic_name": "brief description (2-3 sentences)", ... }
    simplified_characteristics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # 12 spheres brief summaries (L3):
    # { "IDENTITY": "summary", "RESOURCES": "summary", ... }
    spheres_brief: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    last_vectorized_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
