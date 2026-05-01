from __future__ import annotations

import pytest


def test_enum_constants_importable():
    from app.models import Color, Style, Material
    assert Color.RED == "red"
    assert Color.MULTI == "multi"
    assert Style.SATCHEL == "satchel"
    assert Style.BELT_BAG == "belt-bag"
    assert Material.LEATHER == "leather"
    assert Material.VEGAN_LEATHER == "vegan leather"


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


@pytest.mark.asyncio
async def test_list_items_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.get(f"/collections/{collection_id}/items")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_item_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.get(f"/collections/{collection_id}/items/{item_id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_item_primary_color(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "blue"},
    )
    assert resp.status_code == 200
    assert resp.json()["primary_color"] == "blue"


@pytest.mark.asyncio
async def test_update_item_style(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"style": "tote"},
    )
    assert resp.status_code == 200
    assert resp.json()["style"] == "tote"


@pytest.mark.asyncio
async def test_update_item_invalid_primary_color_returns_422(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "purple"},
    )
    assert resp.status_code == 422
