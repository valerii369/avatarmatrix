import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import (
    auth, profile, sync, reflect, session, onboarding_ai, 
    diary, cards, calc, game, match, portrait, retro, 
    voice, payments, master_hub, economy
)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="AVATAR Платформа",
    version="1.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://avatar.aiguro.pro",
        "https://frontend-omega-seven-47.vercel.app",
        "https://frontend-4smscc1it-valerii369s-projects.vercel.app",
        "http://localhost:3000",
        "http://103.74.92.72.nip.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(calc.router,     prefix="/api/calc",     tags=["Calc"])
app.include_router(onboarding_ai.router, prefix="/api/onboarding/ai", tags=["Onboarding"])
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
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(master_hub.router, prefix="/api/master-hub", tags=["MasterHub"])
app.include_router(economy.router,    prefix="/api/economy",    tags=["Economy"])


@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "version": app.version, "env": settings.ENVIRONMENT}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
