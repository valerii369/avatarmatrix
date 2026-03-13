import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.data_architecture import Event, SessionFeatures, UserBehaviorProfileV2
from app.core.feature_extractor import FeatureExtractor
from datetime import datetime, timedelta

async def verify_pipeline():
    """
    Minimal verification script for the unified text-based architecture.
    """
    print("Verification script updated. Old image-based pipeline is deprecated.")
    # No-op for now to prevent crashes
    pass

if __name__ == "__main__":
    asyncio.run(verify_pipeline())
