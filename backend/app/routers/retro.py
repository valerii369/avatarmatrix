from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date, timedelta

from app.database import get_db
from app.models import CardProgress, AlignSession, SyncSession
from app.core.economy import get_sphere_awareness

router = APIRouter()

SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]


@router.get("/{user_id}/week")
async def weekly_retro(user_id: int, db: AsyncSession = Depends(get_db)):
    week_ago = date.today() - timedelta(days=7)

    # Sessions this week
    align_result = await db.execute(
        select(AlignSession).where(
            AlignSession.user_id == user_id,
            AlignSession.created_at >= week_ago,
        )
    )
    align_sessions = align_result.scalars().all()

    sync_result = await db.execute(
        select(SyncSession).where(
            SyncSession.user_id == user_id,
            SyncSession.created_at >= week_ago,
            SyncSession.is_complete == True,
        )
    )
    sync_sessions = sync_result.scalars().all()

    # Cards progress
    cards_result = await db.execute(
        select(CardProgress).where(CardProgress.user_id == user_id)
    )
    all_cards = cards_result.scalars().all()

    # Sphere summary
    sphere_summary = {}
    for sphere in SPHERES:
        sphere_cards = [c for c in all_cards if c.sphere == sphere]
        played = [c for c in sphere_cards if c.hawkins_peak > 0]
        min_h = min((c.hawkins_peak for c in played), default=0)
        avg_h = int(sum(c.hawkins_peak for c in played) / len(played)) if played else 0
        sphere_summary[sphere] = {
            "awareness": get_sphere_awareness(min_h),
            "cards_played": len(played),
            "avg_hawkins": avg_h,
            "min_hawkins": min_h,
        }

    # Hawkins dynamics this week
    hawkins_dynamics = []
    for s in sorted(sync_sessions, key=lambda x: x.created_at):
        hawkins_dynamics.append({
            "date": s.created_at.date().isoformat() if s.created_at else None,
            "archetype_id": s.archetype_id,
            "sphere": s.sphere,
            "hawkins": s.hawkins_score,
        })

    # Recommendations (spheres with least cards played)
    sorted_spheres = sorted(sphere_summary.items(), key=lambda x: (x[1]["cards_played"], x[1]["avg_hawkins"]))
    recommendations = [s[0] for s in sorted_spheres[:3]]

    return {
        "period": "week",
        "sync_sessions_count": len(sync_sessions),
        "align_sessions_count": len(align_sessions),
        "sphere_summary": sphere_summary,
        "hawkins_dynamics": hawkins_dynamics,
        "focus_recommendations": recommendations,
    }


@router.get("/{user_id}/month")
async def monthly_retro(user_id: int, db: AsyncSession = Depends(get_db)):
    month_ago = date.today() - timedelta(days=30)

    cards_result = await db.execute(select(CardProgress).where(CardProgress.user_id == user_id))
    all_cards = cards_result.scalars().all()

    cards_by_rank = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for c in all_cards:
        cards_by_rank[c.rank] = cards_by_rank.get(c.rank, 0) + 1

    synced = len([c for c in all_cards if c.status in ("synced", "aligning", "aligned")])
    total_xp = sum(c.hawkins_peak for c in all_cards if c.hawkins_peak > 0)

    return {
        "period": "month",
        "cards_synced": synced,
        "total_xp_gained": total_xp,
        "cards_by_rank": cards_by_rank,
    }
