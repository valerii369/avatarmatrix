"""
Economy service: handles ✦ Energy credits, token budgets, and streak logic.
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models import User, GameState
from app.config import settings


STREAK_BONUSES = {
    7: 15,
    14: 25,
    21: 40,
    30: 50,
}

TITLES_BY_ACTIONS = {
    "first_login": "Искатель",
    "first_card": "Ученик",
    "cards_10": "Исследователь",
    "first_sphere": "Хранитель",
    "level_25": "Адепт",
    "level_50": "Мастер пути",
    "all_spheres": "Архитектор Судьбы",
    "first_5star": "Просветлённый",
    "level_100": "∞",
}

ENERGY_ACTIONS = {
    "daily_login": lambda streak: 5 + streak,  # max 35
    "daily_reflection": 10,
    "diary_entry": 10,
    "integration_done": 20,
    "card_rank_up": 25,
    "sphere_milestone": 150,
    "invite_friend": 50,
}

ENERGY_COSTS = {
    "mini_session": settings.ENERGY_COST_MINI_SESSION,
    "sync": settings.ENERGY_COST_SYNC,
    "deep_session": settings.ENERGY_COST_DEEP_SESSION,
}


async def award_energy(db: AsyncSession, user: User, action: str, amount: Optional[int] = None) -> int:
    """Award energy for an action. Returns actual amount awarded."""
    if amount is None:
        action_val = ENERGY_ACTIONS.get(action)
        if callable(action_val):
            amount = action_val(user.streak)
        else:
            amount = action_val or 0

    # Cap daily login bonus at 35
    if action == "daily_login":
        amount = min(amount, 35)

    # Premium: no limits (but keep energy for display)
    user.energy += amount
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


async def update_streak(db: AsyncSession, user: User) -> tuple[int, int]:
    """
    Update user streak on daily login.
    Returns (new_streak, bonus_energy).
    """
    today = date.today()
    last = user.last_activity.date() if user.last_activity else None

    bonus = 0

    if last is None:
        user.streak = 1
    elif last == today:
        pass  # Already logged in today
    elif (today - last).days == 1:
        user.streak += 1
        # Check for streak milestones
        bonus = STREAK_BONUSES.get(user.streak, 0)
        if bonus:
            user.energy += bonus
    else:
        user.streak = 1  # Reset streak

    user.last_activity = datetime.utcnow()
    db.add(user)
    return user.streak, bonus


def calculate_xp_for_level(level: int) -> int:
    """Calculate total XP needed to reach a level (RPG curve)."""
    if level <= 1:
        return 0
    # Curve: level 10 = 500, level 50 = 7500, level 100 = 50000
    return int(5 * level ** 2.3)


def hawkins_to_rank(hawkins_peak: int) -> int:
    """Convert peak Hawkins score to card rank (0-5)."""
    if hawkins_peak >= 700:
        return 5  # ⭐⭐⭐⭐⭐ Просветлённый
    elif hawkins_peak >= 540:
        return 4  # ⭐⭐⭐⭐ Мудрец
    elif hawkins_peak >= 400:
        return 3  # ⭐⭐⭐ Мастер
    elif hawkins_peak >= 250:
        return 2  # ⭐⭐ Осознающий
    elif hawkins_peak >= 175:
        return 1  # ⭐ Пробуждающийся
    else:
        return 0  # ☆ Спящий


RANK_NAMES = {
    0: "☆ Спящий",
    1: "⭐ Пробуждающийся",
    2: "⭐⭐ Осознающий",
    3: "⭐⭐⭐ Мастер",
    4: "⭐⭐⭐⭐ Мудрец",
    5: "⭐⭐⭐⭐⭐ Просветлённый",
}

SPHERE_AWARENESS_NAMES = {
    (0, 175): "В тени",
    (175, 250): "Пробуждается",
    (250, 400): "Осознана",
    (400, 540): "Мастерство",
    (540, 700): "Мудрость",
    (700, 1001): "Просветлена",
}


def get_sphere_awareness(min_hawkins: int) -> str:
    """Get sphere awareness level from minimum Hawkins score in sphere."""
    for (low, high), name in SPHERE_AWARENESS_NAMES.items():
        if low <= min_hawkins < high:
            return name
    return "В тени"
