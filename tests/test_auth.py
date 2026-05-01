from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_request_magic_link(db_client):
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_verify_magic_link_valid_token(db_client):
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    resp = await db_client.get(f"/auth/verify?token={token}")
    assert resp.status_code == 200
    assert "session_id" in resp.json()


@pytest.mark.asyncio
async def test_verify_magic_link_creates_user(db_client):
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    resp = await db_client.get(f"/auth/verify?token={token}")
    session_id = resp.json()["session_id"]
    resp = await db_client.get("/auth/me", cookies={"session_id": session_id})
    assert resp.status_code == 200
    assert resp.json()["email"] == "rachel@example.com"


@pytest.mark.asyncio
async def test_verify_magic_link_expired_token(db_client):
    resp = await db_client.get("/auth/verify?token=expired-garbage")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_session_persists(db_client):
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    resp = await db_client.get(f"/auth/verify?token={token}")
    session_id = resp.json()["session_id"]
    resp = await db_client.get("/auth/me", cookies={"session_id": session_id})
    assert resp.status_code == 200
    assert resp.json()["email"] == "rachel@example.com"


@pytest.mark.asyncio
async def test_me_without_session_returns_401(db_client):
    resp = await db_client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(db_client):
    # Login
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    resp = await db_client.get(f"/auth/verify?token={token}")
    session_id = resp.json()["session_id"]
    # Logout
    resp = await db_client.post("/auth/logout", cookies={"session_id": session_id})
    assert resp.status_code == 200
    # Session should be invalid now
    resp = await db_client.get("/auth/me", cookies={"session_id": session_id})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_token_reuse_returns_401(db_client):
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    resp1 = await db_client.get(f"/auth/verify?token={token}")
    assert resp1.status_code == 200
    resp2 = await db_client.get(f"/auth/verify?token={token}")
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_magic_link_missing_email_returns_422(db_client):
    resp = await db_client.post("/auth/magic-link", json={})
    assert resp.status_code == 422
