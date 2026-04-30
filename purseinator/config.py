from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "PURSEINATOR_"}

    database_url: str = "sqlite+aiosqlite:///./purseinator.db"
    photo_storage_root: Path = Path("./photos")
    secret_key: str = "change-me-in-production"
    magic_link_expiry_minutes: int = 15
    session_expiry_days: int = 30
    dev_mode: bool = True


def get_settings() -> Settings:
    return Settings()
