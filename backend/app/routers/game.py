from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, CardProgress, GameState
from app.core.economy import hawkins_to_rank, RANK_NAMES, get_sphere_awareness, calculate_xp_for_level

router = APIRouter()

SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]


@router.get("/{user_id}")
async def get_game_state(user_id: int, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cards_result = await db.execute(select(CardProgress).where(CardProgress.user_id == user_id))
    all_cards = cards_result.scalars().all()

    # Sphere awareness
    sphere_data = {}
    for sphere in SPHERES:
        sphere_cards = [c for c in all_cards if c.sphere == sphere and c.hawkins_peak > 0]
        min_hawkins = min((c.hawkins_peak for c in sphere_cards), default=0)
        sphere_data[sphere] = {
            "awareness": get_sphere_awareness(min_hawkins),
            "min_hawkins": min_hawkins,
            "cards_played": len(sphere_cards),
        }

    # XP needed for next level
    current_level = user.evolution_level
    xp_current = calculate_xp_for_level(current_level)
    xp_next = calculate_xp_for_level(current_level + 1)
    xp_progress = max(0, user.xp - xp_current)
    xp_needed = xp_next - xp_current

    gs_result = await db.execute(select(GameState).where(GameState.user_id == user_id))
    game_state = gs_result.scalar_one_or_none()

    return {
        "energy": user.energy,
        "streak": user.streak,
        "evolution_level": user.evolution_level,
        "xp": user.xp,
        "xp_progress": xp_progress,
        "xp_needed": xp_needed,
        "title": user.title,
        "sphere_data": sphere_data,
        "titles_unlocked": game_state.titles_unlocked if game_state else [],
        "is_premium": user.is_premium,
    }
