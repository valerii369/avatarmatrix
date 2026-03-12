from typing import Optional
from sqlalchemy import Integer, ForeignKey, String, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin

class ReflectionSession(Base, TimestampMixin):
    __tablename__ = "reflection_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    sphere: Mapped[str] = mapped_column(String(32), default="IDENTITY")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_phase: Mapped[int] = mapped_column(Integer, default=1) # 1: Entrance, 2: Descent, 3: Shift, 4: Integration
    
    # Full chat history: [{role, content, timestamp}]
    messages_json: Mapped[Optional[list]] = mapped_column(JSONB, default=[])
    
    # Final results stored after "Finish Session"
    final_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
