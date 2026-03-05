from typing import Optional
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin

class AIDiagnosticSession(Base, TimestampMixin):
    """Stores the initial AI Diagnostic onboarding chat and resulting recommendations."""
    __tablename__ = "ai_diagnostic_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, unique=True)
    
    chat_history_json: Mapped[list] = mapped_column(JSONB, default=[])
    ai_recommendations_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
