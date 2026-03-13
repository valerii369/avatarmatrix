"""
Economy service: handles ✦ Energy credits, token budgets, and streak logic.
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User, GameState
from app.config import settings


XP_VALUES = {
    "card_opened": 100,
    "card_rank_bonus_10": 1000,
    "diary_entry": 25,
    "integration_success": 50,
    "integration_failure": 10,
    "streak_7": 200,
    "streak_30": 1000,
    "sphere_opened": 1000,
    "sphere_mastered": 5000,
}

# XP per rank up (from N to N+1) - 10 level curve
CARD_RANK_UP_XP = {
    1: 40, 2: 80, 3: 150, 4: 250, 5: 400, 6: 600, 7: 850, 8: 1100, 9: 1500
}

TITLES_BY_LEVEL = [
    (1, "Пробуждённый"),
    (6, "Искатель"),
    (11, "Странник"),
    (16, "Осознающий"),
    (21, "Исследователь"),
    (26, "Практик"),
    (31, "Трансформирующий"),
    (36, "Адепт"),
    (41, "Проводник"),
    (46, "Мастер"),
    (51, "Хранитель"),
    (56, "Созидатель"),
    (61, "Визионер"),
    (66, "Властелин"),
    (71, "Мудрец"),
    (76, "Философ Света"),
    (81, "Провидец"),
    (86, "Архитектор"),
    (91, "Владыка Судьбы"),
    (96, "Квантовый Архитектор"),
]

REFERRAL_BONUS_JOINER = 200
REFERRAL_BONUS_REFERRER = 100
REFERRAL_PURCHASE_BONUS = 100

ENERGY_ACTIONS = {
    "referral_join": REFERRAL_BONUS_JOINER,
    "referral_invite": REFERRAL_BONUS_REFERRER,
    "referral_purchase": REFERRAL_PURCHASE_BONUS,
}

ENERGY_COSTS = {
    "sync": settings.ENERGY_COST_SYNC,
    "alignment": settings.ENERGY_COST_ALIGNMENT,
    "reflection_ai": settings.ENERGY_COST_REFLECTION_AI,
    "reflection_simple": settings.ENERGY_COST_REFLECTION_SIMPLE,
    "deep_session": settings.ENERGY_COST_DEEP_SESSION,
}


async def award_xp(db: AsyncSession, user: User, amount: int):
    """Award XP, handle level-ups and titles."""
    if amount <= 0:
        return
    
    user.xp = (user.xp or 0) + amount
    
    # Level up check
    while user.evolution_level < 100:
        next_lvl = user.evolution_level + 1
        needed = calculate_xp_for_level(next_lvl)
        if user.xp >= needed:
            user.evolution_level = next_lvl
            # Update title if milestone reached
            user.title = get_level_title(user.evolution_level)
        else:
            break
    
    db.add(user)


def get_level_title(level: int) -> str:
    """Get title based on evolution level."""
    current_title = "Пробуждённый"
    for threshold, title in TITLES_BY_LEVEL:
        if level >= threshold:
            current_title = title
        else:
            break
    return current_title


async def process_card_rank_up(db: AsyncSession, user: User, old_rank: int, new_rank: int, session_hawkins: int):
    """
    Handle card rank advancement: award incremental XP for each level jumped
    plus milestone bonuses for LVL 10 and 20.
    """
    if new_rank <= old_rank:
        return
    
    total_xp = 0
    for r in range(old_rank, new_rank):
        # r is the current rank, we award XP for reaching r+1
        xp_gain = CARD_RANK_UP_XP.get(r, 0)
        total_xp += xp_gain
        
        # Milestone bonuses
        if r + 1 == 10:
            total_xp += XP_VALUES["card_rank_bonus_10"]
            
    await award_xp(db, user, total_xp)


async def check_sphere_milestones(db: AsyncSession, user: User, sphere: str):
    """Check if sphere is fully opened or mastered and award XP."""
    from app.models import CardProgress
    
    # Get all 22 cards for this sphere
    result = await db.execute(
        select(CardProgress).where(
            CardProgress.user_id == user.id,
            CardProgress.sphere == sphere
        )
    )
    cards = result.scalars().all()
    
    if len(cards) < 22:
        return # Not all cards even exist yet (natal chart not fully processed?)

    all_opened = all(c.sync_sessions_count > 0 for c in cards)
    all_mastered = all(c.rank >= 10 for c in cards)
    
    # Fetch user's GameState
    stmt = select(GameState).where(GameState.user_id == user.id)
    gs_result = await db.execute(stmt)
    game_state = gs_result.scalar_one_or_none()
    
    if not game_state:
        # Create it if it somehow missing
        game_state = GameState(user_id=user.id)
        db.add(game_state)
        
    awarded = game_state.milestones_awarded or []
    milestone_opened_key = f"{sphere}_opened"
    milestone_mastered_key = f"{sphere}_mastered"

    if all_opened and milestone_opened_key not in awarded:
        await award_xp(db, user, XP_VALUES["sphere_opened"])
        # Avoid mutating JSON directly in SQLAlchemy, assign a new updated list
        game_state.milestones_awarded = awarded + [milestone_opened_key]
        awarded = game_state.milestones_awarded
        db.add(game_state)

    if all_mastered and milestone_mastered_key not in awarded:
        await award_xp(db, user, XP_VALUES["sphere_mastered"])
        game_state.milestones_awarded = awarded + [milestone_mastered_key]
        db.add(game_state)


async def process_referral_reward(db: AsyncSession, user: User):
    """
    Award energy to new user and their referrer.
    Called after onboarding is complete.
    """
    # 1. Award Joiner Bonus
    if user.referred_by:
        await award_energy(db, user, "referral_join")
        
        # 2. Award Referrer Bonus
        referrer_result = await db.execute(select(User).where(User.id == user.referred_by))
        referrer = referrer_result.scalar_one_or_none()
        if referrer:
            await award_energy(db, referrer, "referral_invite")


async def award_energy(db: AsyncSession, user: User, action: str, amount: Optional[int] = None) -> int:
    """Award energy for an action. Returns actual amount awarded."""
    if amount is None:
        amount = ENERGY_ACTIONS.get(action, 0)

    if amount <= 0:
        return 0

    user.energy = (user.energy or 0) + amount
    db.add(user)
    return amount


async def spend_energy(db: AsyncSession, user: User, action: str) -> bool:
    """
    Spend energy for an action.
    Returns True if successful, False if insufficient energy.
    """
    cost = ENERGY_COSTS.get(action, 0)
    if user.is_premium:
        return True  # Premium: always allowed

    if user.energy < cost:
        return False

    user.energy -= cost
    db.add(user)
    return True


async def update_streak(db: AsyncSession, user: User) -> tuple[int, int, bool]:
    """
    Update user streak on daily login.
    Returns (new_streak, bonus_xp, is_new_day).
    """
    today = date.today()
    last = user.last_activity.date() if user.last_activity else None

    bonus_xp = 0
    is_new_day = False

    if last is None:
        user.streak = 1
        is_new_day = True
    elif last == today:
        is_new_day = False
    elif (today - last).days == 1:
        user.streak += 1
        is_new_day = True
        # Check for XP streak milestones
        if user.streak == 7:
            bonus_xp = XP_VALUES["streak_7"]
        elif user.streak == 30:
            bonus_xp = XP_VALUES["streak_30"]
        
        if bonus_xp:
            await award_xp(db, user, bonus_xp)
    else:
        user.streak = 1  # Reset streak
        is_new_day = True

    user.last_activity = datetime.utcnow()
    db.add(user)
    return user.streak, bonus_xp, is_new_day


def calculate_xp_for_level(level: int) -> int:
    """
    Calculate total XP needed to reach a level (RPG curve).
    Using a smooth, progressively harder curve: XP = 20 * (Level^2.3)
    """
    if level <= 1:
        return 0
    return int(30 * level ** 2.3)


def hawkins_to_rank(hawkins_peak: int) -> int:
    """
    Convert peak Hawkins score to card level (1-10) according to new logic.
    LVL 1: 0-20
    LVL 2: 21-50
    LVL 3: 51-100
    LVL 4: 101-175
    LVL 5: 176-200 (Мужество)
    LVL 6: 201-310
    LVL 7: 311-400
    LVL 8: 401-500
    LVL 9: 501-600
    LVL 10: 601-1000
    """
    if hawkins_peak <= 0: return 0
    if hawkins_peak <= 20: return 1
    if hawkins_peak <= 50: return 2
    if hawkins_peak <= 100: return 3
    if hawkins_peak <= 175: return 4
    if hawkins_peak <= 200: return 5
    if hawkins_peak <= 310: return 6
    if hawkins_peak <= 400: return 7
    if hawkins_peak <= 500: return 8
    if hawkins_peak <= 600: return 9
    return 10


RANK_NAMES = {i: f"LVL {i}" for i in range(11)}
RANK_NAMES[0] = "☆ Спящий"

SPHERE_AWARENESS_NAMES = {
    (0, 175): "В тени",
    (175, 200): "Пробуждается",
    (200, 400): "Осознана",
    (400, 500): "Мастерство",
    (500, 600): "Мудрость",
    (600, 1001): "Просветлена",
}


def get_sphere_awareness(min_hawkins: int) -> str:
    """Get sphere awareness level from minimum Hawkins score in sphere."""
    for (low, high), name in SPHERE_AWARENESS_NAMES.items():
        if low <= min_hawkins < high:
            return name
    return "В тени"
