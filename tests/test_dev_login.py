from __future__ import annotations

import pytest
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import create_app
from app.models import Base


@pytest.mark.asyncio
async def test_dev_login_works_in_dev_mode(db_client):
    resp = await db_client.post("/auth/dev-login")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["email"] == "dev@purseinator.local"


@pytest.mark.asyncio
async def test_dev_login_session_is_valid(db_client):
    resp = await db_client.post("/auth/dev-login")
    session_id = resp.json()["session_id"]
    db_client.cookies.set("session_id", session_id)
    resp = await db_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "dev@purseinator.local"


@pytest.mark.asyncio
async def test_dev_login_blocked_in_prod():
    """Dev login endpoint must return 404 when dev_mode is False."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    with patch("app.routes.auth.get_settings") as mock_settings:
        mock_settings.return_value.dev_mode = False
        mock_settings.return_value.secret_key = "test-secret-key-that-is-long"
        mock_settings.return_value.magic_link_expiry_minutes = 15
        mock_settings.return_value.session_expiry_days = 30

        app = create_app(session_factory=session_factory, photo_storage_root="/tmp")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/auth/dev-login")
            assert resp.status_code == 404

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def test_dev_button_stripped_from_prod_build():
    """Verify the production frontend build does not contain dev login references."""
    from pathlib import Path

    dist = Path(__file__).parent.parent / "frontend" / "dist"
    if not dist.exists():
        pytest.skip("frontend not built — run 'npm run build' in frontend/")

    for js_file in dist.rglob("*.js"):
        content = js_file.read_text()
        assert "dev-login" not in content, (
            f"Production JS bundle {js_file.name} contains 'dev-login' — "
            "the dev login button must not ship to production"
        )
