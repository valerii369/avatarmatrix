from typing import Optional
from sqlalchemy import Integer, ForeignKey, String, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class RiverResult(Base, TimestampMixin):
    """
    Stores outputs from Level 2 (River) processing for specific domains.
    Allows for multiple systems (Astrology, Numerology, etc.) to store 
    independent interpretations before final Ocean synthesis.
    """
    __tablename__ = "river_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    
    # Domain of the interpretation: 'astrology', 'numerology', 'human_design', etc.
    domain: Mapped[str] = mapped_column(String(64), index=True)
    
    # The actual interpretation data (e.g., the 12 spheres)
    interpretation_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    
    # Version of the synthesis logic/prompt used
    logic_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Index for fast retrieval of specific domain results for a user
    __table_args__ = (
        Index("ix_river_results_user_domain", "user_id", "domain", unique=True),
    )
