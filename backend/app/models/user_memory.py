from typing import Optional
from sqlalchemy import Integer, ForeignKey, Text, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.models.base import TimestampMixin

class UserMemory(Base, TimestampMixin):
    """
    Stores semantic 'atomic insights' or key facts about the user.
    Used by the Assistant to remember details across sessions.
    """
    __tablename__ = "user_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)
    
    # source: assistant, sync, manual, etc.
    source: Mapped[str] = mapped_column(String(32), default="assistant")
    
    # metadata: session_id, relevance score, importance, etc.
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    def __repr__(self):
        return f"<UserMemory id={self.id} user_id={self.user_id} source={self.source}>"
