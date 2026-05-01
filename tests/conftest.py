from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import create_app
from app.models import Base


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_engine():
    from sqlalchemy import event

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    # Enable SQLite foreign key enforcement (must be done per-connection)
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(db_session_factory):
    """Provide a single AsyncSession for direct DB manipulation in tests."""
    async with db_session_factory() as session:
        yield session


@pytest.fixture
def photo_storage_root(tmp_path):
    return str(tmp_path / "photos")


@pytest.fixture
async def db_client(db_engine, db_session_factory, photo_storage_root):
    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client(db_engine, db_session_factory, photo_storage_root):
    """A test client that is already authenticated as a curator."""
    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login
        resp = await ac.post("/auth/magic-link", json={"email": "rachel@example.com"})
        token = resp.json()["token"]
        resp = await ac.get(f"/auth/verify?token={token}")
        session_id = resp.json()["session_id"]
        ac.cookies.set("session_id", session_id)
        yield ac


@pytest.fixture
def purse_fixtures():
    """Returns a callable that resolves a fixture name to its Path."""
    base = Path(__file__).parent / "fixtures" / "purses"

    def _get(name: str) -> Path:
        path = base / f"{name}.png"
        if not path.exists():
            raise FileNotFoundError(f"purse fixture {name!r} not found at {path}")
        return path

    return _get


@pytest.fixture
async def other_auth_client(db_engine, db_session_factory, photo_storage_root):
    """A test client authenticated as a different user (kimberly), for ownership checks."""
    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/magic-link", json={"email": "kimberly@example.com"})
        token = resp.json()["token"]
        resp = await ac.get(f"/auth/verify?token={token}")
        ac.cookies.set("session_id", resp.json()["session_id"])
        yield ac
