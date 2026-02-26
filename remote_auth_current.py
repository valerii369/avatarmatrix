"""
Auth router: Telegram initData verification + user creation.
"""
import hashlib
import hmac
import json
from urllib.parse import unquote, parse_qsl

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, GameState
from app.config import settings
from app.core.economy import update_streak, award_energy

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
    token: str  # simplified: tg_id as token (use JWT in production)


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
    return user_data


@router.post("", response_model=AuthResponse)
async def authenticate(
    request: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate via Telegram initData."""
    if request.test_mode and settings.ENVIRONMENT == "development":
        # Allow test users in development
        tg_user = {"id": 12345678, "first_name": "Test", "last_name": "User", "username": "testuser"}
    else:
        try:
            tg_user = verify_telegram_initdata(request.initData, settings.BOT_TOKEN)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid initData")

    tg_id = tg_user["id"]

    # Find or create user
    result = await db.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    is_new = False
    if not user:
        user = User(
            tg_id=tg_id,
            first_name=tg_user.get("first_name", ""),
            last_name=tg_user.get("last_name", ""),
            tg_username=tg_user.get("username", ""),
            energy=100,
            streak=0,
            evolution_level=1,
            title="Искатель",
        )
        db.add(user)
        await db.flush()

        # Create game state
        game_state = GameState(user_id=user.id)
        db.add(game_state)
        is_new = True

    # Update streak on login
    new_streak, bonus = await update_streak(db, user)
    if not is_new:
        await award_energy(db, user, "daily_login")

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
        token=str(user.tg_id),
    )
