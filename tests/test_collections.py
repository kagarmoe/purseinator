from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from purseinator.main import create_app


@pytest.fixture
async def other_auth_client(db_engine, db_session_factory, photo_storage_root):
    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/magic-link", json={"email": "kimberly@example.com"})
        token = resp.json()["token"]
        resp = await ac.get(f"/auth/verify?token={token}")
        session_id = resp.json()["session_id"]
        ac.cookies.set("session_id", session_id)
        yield ac


@pytest.mark.asyncio
async def test_create_collection(auth_client):
    resp = await auth_client.post(
        "/collections", json={"name": "Rachel's Bags", "description": "The big purge"}
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Rachel's Bags"


@pytest.mark.asyncio
async def test_create_collection_with_dollar_goal(auth_client):
    resp = await auth_client.post(
        "/collections", json={"name": "Bags", "dollar_goal": 5000.0}
    )
    assert resp.status_code == 201
    assert resp.json()["dollar_goal"] == 5000.0


@pytest.mark.asyncio
async def test_list_collections(auth_client):
    await auth_client.post("/collections", json={"name": "Bags"})
    resp = await auth_client.get("/collections")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_collection(auth_client):
    resp = await auth_client.post("/collections", json={"name": "Bags"})
    coll_id = resp.json()["id"]
    resp = await auth_client.get(f"/collections/{coll_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Bags"


@pytest.mark.asyncio
async def test_get_collection_not_found(auth_client):
    resp = await auth_client.get("/collections/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_create_collection(db_client):
    resp = await db_client.post("/collections", json={"name": "Bags"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_collection_non_owner_returns_403(auth_client, other_auth_client):
    resp = await auth_client.post("/collections", json={"name": "Rachel's Bags"})
    coll_id = resp.json()["id"]
    resp = await other_auth_client.get(f"/collections/{coll_id}")
    assert resp.status_code == 403
