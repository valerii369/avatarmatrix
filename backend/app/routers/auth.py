"""
Auth router: Telegram initData verification + user creation.
"""
import hashlib
import hmac
import json
import secrets
from urllib.parse import unquote, parse_qsl

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, GameState
from app.config import settings
from app.core.economy import update_streak, award_energy, award_xp, XP_VALUES, calculate_xp_for_level

router = APIRouter()


class TelegramAuthRequest(BaseModel):
    initData: str
    test_mode: bool = False


class AuthResponse(BaseModel):
    user_id: int
    tg_id: int
    first_name: str
    onboarding_done: bool
    energy: int
    streak: int
    evolution_level: int
    title: str
    xp: int
    xp_current: int
    xp_next: int
    token: str  # simplified: tg_id as token (use JWT in production)
    referral_code: str
    photo_url: Optional[str] = None


def generate_referral_code() -> str:
    """Generate a unique 8-character alphanumeric referral code."""
    return secrets.token_hex(4).upper()


def verify_telegram_initdata(init_data: str, bot_token: str) -> dict:
    """Verify Telegram WebApp initData signature."""
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", "")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(received_hash, expected_hash):
        raise ValueError("Invalid initData signature")

    user_data = json.loads(parsed.get("user", "{}"))
    return {"user": user_data, "start_param": parsed.get("start_param")}


@router.post("", response_model=AuthResponse)
async def authenticate(
    request: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate via Telegram initData."""
    if request.test_mode and settings.ENVIRONMENT == "development":
        # Allow test users in development
        tg_user = {"id": 12345678, "first_name": "Test", "last_name": "User", "username": "testuser"}
        start_param = None
    else:
        try:
            tg_data = verify_telegram_initdata(request.initData, settings.BOT_TOKEN)
            tg_user = tg_data["user"]
            start_param = tg_data["start_param"]
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid initData")

    tg_id = tg_user.get("id")

    # Find or create user
    result = await db.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    is_new = False
    if not user:
        # Check start_param for referral
        referred_by_id = None
        if start_param:
            referrer_result = await db.execute(select(User).where(User.referral_code == start_param))
            referrer = referrer_result.scalar_one_or_none()
            if referrer:
                referred_by_id = referrer.id

        user = User(
            tg_id=tg_id,
            first_name=tg_user.get("first_name", ""),
            last_name=tg_user.get("last_name", ""),
            tg_username=tg_user.get("username", ""),
            energy=10000,
            streak=0,
            evolution_level=1,
            title="Искатель",
            referral_code=generate_referral_code(),
            referred_by=referred_by_id,
            photo_url=tg_user.get("photo_url")
        )
        db.add(user)
        await db.flush()

        # Create game state
        game_state = GameState(user_id=user.id)
        db.add(game_state)
        is_new = True
    else:
        is_new = False
        # Update photo_url if changed
        new_photo = tg_user.get("photo_url")
        if new_photo and user.photo_url != new_photo:
            user.photo_url = new_photo
            db.add(user)

    # Update streak on login
    new_streak, bonus_xp, is_new_day = await update_streak(db, user)
    if not is_new and is_new_day:
        # await award_energy(db, user, "daily_login")  # Disabled per new tokenomics
        pass

    await db.commit()
    await db.refresh(user)

    return AuthResponse(
        user_id=user.id,
        tg_id=user.tg_id,
        first_name=user.first_name or "",
        onboarding_done=user.onboarding_done,
        energy=user.energy,
        streak=user.streak,
        evolution_level=user.evolution_level,
        title=user.title,
        xp=user.xp,
        xp_current=calculate_xp_for_level(user.evolution_level),
        xp_next=calculate_xp_for_level(user.evolution_level + 1),
        token=str(user.tg_id),
        referral_code=user.referral_code or "",
        photo_url=user.photo_url
    )
