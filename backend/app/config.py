from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str
    BOT_TOKEN: str
    OPENAI_API_KEY: str
    OWNER_TG_ID: int = 0  # TG ID for 1000 starting energy
    MINI_APP_URL: str = "https://your-app.vercel.app"
    API_BASE_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # OpenAI model settings
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MODEL_FAST: str = "gpt-4o-mini"

    # Token budgets (hidden from user)
    TOKEN_BUDGET_REFLECTION: int = 800
    TOKEN_BUDGET_MINI_SESSION: int = 2500
    TOKEN_BUDGET_SYNC: int = 12000
    TOKEN_BUDGET_DEEP_SESSION: int = 4000

    # Energy costs
    ENERGY_COST_SYNC: int = 35
    ENERGY_COST_ALIGNMENT: int = 20
    ENERGY_COST_REFLECTION_AI: int = 20
    ENERGY_COST_REFLECTION_SIMPLE: int = 5
    ENERGY_COST_DEEP_SESSION: int = 50

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
