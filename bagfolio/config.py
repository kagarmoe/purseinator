from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "BAGFOLIO_"}

    database_url: str = "sqlite+aiosqlite:///./bagfolio.db"
    photo_storage_root: Path = Path("./photos")
    secret_key: str = "change-me-in-production"
    magic_link_expiry_minutes: int = 15
    session_expiry_days: int = 30


def get_settings() -> Settings:
    return Settings()
