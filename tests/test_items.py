from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from purseinator.main import create_app


@pytest.fixture
async def collection_id(auth_client):
    resp = await auth_client.post("/collections", json={"name": "Test Collection"})
    return resp.json()["id"]


@pytest.fixture
async def item_id(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items", json={"brand": "Coach"}
    )
    return resp.json()["id"]


@pytest.fixture
async def other_auth_client(db_engine, db_session_factory, photo_storage_root):
    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/magic-link", json={"email": "kimberly@example.com"})
        token = resp.json()["token"]
        resp = await ac.get(f"/auth/verify?token={token}")
        ac.cookies.set("session_id", resp.json()["session_id"])
        yield ac


@pytest.mark.asyncio
async def test_create_item(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items",
        json={"brand": "Coach", "status": "undecided"},
    )
    assert resp.status_code == 201
    assert resp.json()["brand"] == "Coach"


@pytest.mark.asyncio
async def test_create_item_unknown_brand(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items", json={"brand": "unknown"}
    )
    assert resp.status_code == 201
    assert resp.json()["brand"] == "unknown"


@pytest.mark.asyncio
async def test_create_item_defaults(auth_client, collection_id):
    resp = await auth_client.post(f"/collections/{collection_id}/items", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert data["brand"] == "unknown"
    assert data["status"] == "undecided"


@pytest.mark.asyncio
async def test_update_item_brand(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"brand": "Louis Vuitton"},
    )
    assert resp.status_code == 200
    assert resp.json()["brand"] == "Louis Vuitton"


@pytest.mark.asyncio
async def test_update_item_status(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"status": "keeper"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "keeper"


@pytest.mark.asyncio
async def test_list_items(auth_client, collection_id):
    await auth_client.post(f"/collections/{collection_id}/items", json={"brand": "A"})
    await auth_client.post(f"/collections/{collection_id}/items", json={"brand": "B"})
    resp = await auth_client.get(f"/collections/{collection_id}/items")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_item(auth_client, collection_id, item_id):
    resp = await auth_client.get(f"/collections/{collection_id}/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id


@pytest.mark.asyncio
async def test_get_item_not_found(auth_client, collection_id):
    resp = await auth_client.get(f"/collections/{collection_id}/items/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_item_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"brand": "Gucci"},
    )
    assert resp.status_code == 403
