spawn ssh -o StrictHostKeyChecking=no root@103.74.92.72 cat /root/avatar/backend/app/main.py
root@103.74.92.72's password: 
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import (
    auth, calc, cards, sync, session,
    diary, profile, portrait, game, voice, retro, match, reflect
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events via lifespan context manager."""
    # Startup
    await init_db()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="AVATAR API",
    description="Платформа эволюции сознания",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, "CORS_ORIGINS") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(calc.router,     prefix="/api/calc",     tags=["Calc"])
app.include_router(cards.router,    prefix="/api/cards",    tags=["Cards"])
app.include_router(sync.router,     prefix="/api/sync",     tags=["Sync"])
app.include_router(session.router,  prefix="/api/session",  tags=["Session"])
app.include_router(diary.router,    prefix="/api/diary",    tags=["Diary"])
app.include_router(profile.router,  prefix="/api/profile",  tags=["Profile"])
app.include_router(portrait.router, prefix="/api/portrait", tags=["Portrait"])
app.include_router(game.router,     prefix="/api/game",     tags=["Game"])
app.include_router(voice.router,    prefix="/api/voice",    tags=["Voice"])
app.include_router(retro.router,    prefix="/api/retro",    tags=["Retro"])
app.include_router(match.router,    prefix="/api/match",    tags=["Match"])
app.include_router(reflect.router,  prefix="/api/reflect",  tags=["Reflect"])


@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "version": "1.0.0", "env": settings.ENVIRONMENT}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
