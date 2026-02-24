"""Routers package."""
from app.routers import (
    auth, calc, cards, sync, session,
    diary, profile, portrait, game, voice, retro, match, reflect
)

__all__ = [
    "auth", "calc", "cards", "sync", "session",
    "diary", "profile", "portrait", "game", "voice", "retro", "match", "reflect"
]
