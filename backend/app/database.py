from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
import logging

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Reconnect on stale connections
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database on startup.
    - Development: auto-creates tables (convenient for local dev)
    - Production: only verifies connection (use 'alembic upgrade head' for schema)
    """
    if settings.ENVIRONMENT == "development":
        logger.warning("⚠️  Development mode: creating tables via SQLAlchemy metadata")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        # In production just test the connection
        async with engine.begin() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("✅ Database connection verified")
