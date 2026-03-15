from typing import Optional, Dict
from sqlalchemy import Integer, ForeignKey, String, Boolean, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin

class AssistantSession(Base, TimestampMixin):
    __tablename__ = "assistant_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Store resonance scores for each sphere in this session: {"IDENTITY": 0.5, ...}
    resonance_scores: Mapped[Optional[dict]] = mapped_column(JSONB, default={})
    
    # Full chat history: [{role, content, timestamp}]
    messages_json: Mapped[Optional[list]] = mapped_column(JSONB, default=[])
    
    # Metadata like first_touch: true/false
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, default={})

    # Final results stored after "Finish Session"
    final_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
