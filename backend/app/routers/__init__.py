"""Routers package."""
from app.routers import (
    auth, calc, cards, sync, session,
    diary, profile, game, voice, retro, match,
    payments, master_hub, assistant, analytics
)

__all__ = [
    "auth", "calc", "cards", "sync", "session",
    "diary", "profile", "game", "voice", "retro", "match",
    "payments", "master_hub", "assistant", "analytics"
]
