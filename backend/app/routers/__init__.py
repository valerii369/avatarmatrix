"""Routers package."""
from app.routers import (
    auth, calc, cards, sync, session,
    diary, profile, portrait, game, voice, retro, match,
    payments, master_hub, assistant
)

__all__ = [
    "auth", "calc", "cards", "sync", "session",
    "diary", "profile", "portrait", "game", "voice", "retro", "match",
    "payments", "master_hub", "assistant"
]
