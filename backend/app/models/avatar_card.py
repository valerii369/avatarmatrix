from sqlalchemy import Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base

class AvatarCard(Base):
    __tablename__ = "avatar_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    archetype_id: Mapped[int] = mapped_column(Integer, index=True)
    sphere: Mapped[str] = mapped_column(String, index=True)
    shadow: Mapped[str] = mapped_column(Text)
    light: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Vector] = mapped_column(Vector(1536))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)
