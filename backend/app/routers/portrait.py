"""
Portrait router: build and retrieve user portrait.
Also exposes next card recommendations.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models import UserPortrait
from app.core.portrait_builder import (
    build_full_portrait,
    get_next_recommended_cards,
)

router = APIRouter()


async def _rebuild_portrait_task(user_id: int):
    """Background task: rebuild portrait in its own DB session."""
    async with AsyncSessionLocal() as session:
        await build_full_portrait(session, user_id)


@router.post("/{user_id}/build")
async def trigger_portrait_build(
    user_id: int,
    background_tasks: BackgroundTasks,
):
    """
    Trigger full portrait rebuild as a background task.
    Called automatically after every completed sync session.
    """
    background_tasks.add_task(_rebuild_portrait_task, user_id)
    return {"message": "Portrait rebuild started"}


@router.get("/{user_id}")
async def get_portrait(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get the full user portrait (all 8 spheres)."""
    result = await db.execute(
        select(UserPortrait).where(UserPortrait.user_id == user_id)
    )
    portraits = result.scalars().all()

    return {
        sphere_data.sphere: {
            "avg_hawkins": sphere_data.avg_hawkins,
            "min_hawkins": sphere_data.min_hawkins,
            "patterns": sphere_data.patterns_json or [],
            "body_map": sphere_data.body_map_json or {},
            "hawkins_timeline": sphere_data.hawkins_timeline or [],
        }
        for sphere_data in portraits
    }


@router.get("/{user_id}/recommend")
async def get_recommendations(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get top 5 recommended cards based on portrait analysis."""
    recommendations = await get_next_recommended_cards(db, user_id, limit=5)
    return {"recommendations": recommendations}
