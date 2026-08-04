
"""
Centralized application configuration.

All secrets/config come from environment variables. Nothing sensitive is
hardcoded here. In production these are injected via the container
orchestrator's secret management, not baked into the image.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # --- Database ---
    DATABASE_URL: str  # e.g. postgresql+psycopg2://user:pass@postgres:5432/contractai

    # --- Auth / JWT ---
    JWT_SECRET_KEY: str  # required, must be set via env — no default on purpose
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # --- Rate limiting ---
    REDIS_URL: str = "redis://redis:6379/0"
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_INTAKE: str = "10/hour"

    # --- File uploads ---
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: tuple = ("image/jpeg", "image/png", "image/webp")
    UPLOAD_STORAGE_PATH: str = "/app/storage/uploads"

    # --- AI providers ---
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # --- Homeowner claim links ---
    CLAIM_LINK_EXPIRE_DAYS: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
    