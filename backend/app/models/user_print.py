from sqlalchemy import Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.base import TimestampMixin

class UserPrint(Base, TimestampMixin):
    """
    SQLAlchemy model for storing the User Print (Digital Passport).
    Stored as JSONB for flexibility and efficient querying.
    """
    __tablename__ = "user_prints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    # The actual print data matching UserPrintSchema
    print_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})

    # Indices for performance on common queries
    __table_args__ = (
        Index("ix_user_prints_data_identity", print_data["identity"], postgresql_using="gin"),
        Index("ix_user_prints_data_psychology", print_data["psychology"], postgresql_using="gin"),
        Index("ix_user_prints_data_spheres", print_data["spheres"], postgresql_using="gin"),
    )
