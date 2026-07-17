from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h

    DATABASE_URL: str
    DEBUG: bool = False

    DEFAULT_ADMIN_EMAIL: str
    DEFAULT_ADMIN_PASSWORD: str
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost",
        "http://frontend",
        "http://frontend:80",
    ]

    # FL Engine paths (relative to /app in Docker)
    FL_ENGINE_PATH: str = "/app"
    DATA_DIR: str = "/app/data"
    RESULTS_DIR: str = "/app/results"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
