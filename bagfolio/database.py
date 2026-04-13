from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bagfolio.config import get_settings


def get_engine(url: str | None = None):
    return create_async_engine(url or get_settings().database_url)


def get_session_factory(engine=None):
    engine = engine or get_engine()
    return async_sessionmaker(engine, expire_on_commit=False)
