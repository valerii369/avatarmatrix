from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, CardProgress, NatalChart, Pattern

router = APIRouter()

SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]


@router.get("/{user_id}")
async def get_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    cards_result = await db.execute(select(CardProgress).where(CardProgress.user_id == user_id))
    all_cards = cards_result.scalars().all()

    patterns_result = await db.execute(select(Pattern).where(Pattern.user_id == user_id))
    patterns = patterns_result.scalars().all()

    # Build fingerprint (for matching — available when spheres ≥500)
    strong_spheres = {}
    for sphere in SPHERES:
        sphere_cards = [c for c in all_cards if c.sphere == sphere and c.hawkins_peak >= 500]
        if len(sphere_cards) == 22:  # All 22 archetypes in sphere ≥500
            avg_h = int(sum(c.hawkins_peak for c in sphere_cards) / 22)
            strong_spheres[sphere] = avg_h

    top_patterns = sorted(patterns, key=lambda p: p.strength, reverse=True)[:3]
    dominant_archetypes = []
    seen = set()
    for c in sorted(all_cards, key=lambda x: x.hawkins_peak, reverse=True):
        if c.archetype_id not in seen:
            dominant_archetypes.append(c.archetype_id)
            seen.add(c.archetype_id)
        if len(dominant_archetypes) == 3:
            break

    fingerprint = {
        "spheres_unlocked": strong_spheres,
        "dominant_archetypes": dominant_archetypes,
        "resolved_patterns": [p.tag for p in top_patterns],
        "evolution_level": user.evolution_level,
        "matching_available": len(strong_spheres) > 0,
    }

    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "birth_place": user.birth_place,
        "energy": user.energy,
        "streak": user.streak,
        "evolution_level": user.evolution_level,
        "title": user.title,
        "fingerprint": fingerprint,
    }
