from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, CardProgress, NatalChart, Pattern
from app.core.economy import calculate_xp_for_level, get_level_title

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

    # Ensure title is synced with level
    expected_title = get_level_title(user.evolution_level)
    if user.title != expected_title:
        user.title = expected_title
        db.add(user)
        # We don't necessarily need a commit here if we assume it's just a sync, 
        # but let's do it to persist the fix.
        await db.commit()
        await db.refresh(user)

    # Referral stats
    referral_count_result = await db.execute(select(User).where(User.referred_by == user.id))
    referrals = referral_count_result.scalars().all()
    referral_count = len(referrals)
    
    # Simple heuristic for bonus calculation: (count * 100) 
    # In a real system, we'd have a separate ledge/history table
    referral_energy_earned = referral_count * 100

    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "birth_place": user.birth_place,
        "energy": user.energy,
        "streak": user.streak,
        "evolution_level": user.evolution_level,
        "title": user.title,
        "xp": user.xp,
        "xp_current": calculate_xp_for_level(user.evolution_level),
        "xp_next": calculate_xp_for_level(user.evolution_level + 1),
        "fingerprint": fingerprint,
        "onboarding_done": user.onboarding_done,
        "referral_code": user.referral_code,
        "referral_count": referral_count,
        "referral_energy_earned": referral_energy_earned,
    }


@router.get("/tg/{tg_id}")
async def get_profile_by_tg(tg_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch user basic data by Telegram ID for bot usage."""
    from fastapi import HTTPException
    user_result = await db.execute(select(User).where(User.tg_id == tg_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "id": user.id,
        "first_name": user.first_name,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "birth_time": user.birth_time,
        "birth_place": user.birth_place,
    }


@router.post("/tg/{tg_id}/reset")
async def reset_profile_by_tg(tg_id: int, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    from sqlalchemy import delete
    from app.models import GameState, SyncSession, AlignSession, DiaryEntry
    
    user_result = await db.execute(select(User).where(User.tg_id == tg_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Clear user onboarding fields
    user.birth_date = None
    user.birth_time = None
    user.birth_place = None
    user.birth_lat = None
    user.birth_lon = None
    user.birth_tz = None
    user.onboarding_done = False
    
    # Clear user progression fields
    user.energy = 10000
    user.streak = 0
    user.evolution_level = 1
    user.xp = 0
    user.title = "Искатель"
    user.last_activity = None
    
    # Reset GameState
    game_state_result = await db.execute(select(GameState).where(GameState.user_id == user.id))
    game_state = game_state_result.scalar_one_or_none()
    if game_state:
        game_state.titles_unlocked = []
        game_state.badges_json = []
        game_state.current_title = "Искатель"
        game_state.daily_energy = 10
        game_state.daily_energy_date = None
        db.add(game_state)
    
    # Delete dependent charts/cards and sessions
    await db.execute(delete(CardProgress).where(CardProgress.user_id == user.id))
    await db.execute(delete(NatalChart).where(NatalChart.user_id == user.id))
    await db.execute(delete(SyncSession).where(SyncSession.user_id == user.id))
    await db.execute(delete(AlignSession).where(AlignSession.user_id == user.id))
    await db.execute(delete(DiaryEntry).where(DiaryEntry.user_id == user.id))
    
    db.add(user)
    await db.commit()
    
    return {"success": True, "message": "Профиль сброшен."}
