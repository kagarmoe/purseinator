from __future__ import annotations

import io

import pytest


@pytest.fixture
async def collection_id(auth_client):
    resp = await auth_client.post("/collections", json={"name": "Photo Test"})
    return resp.json()["id"]


@pytest.fixture
async def item_id(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items", json={"brand": "Coach"}
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_upload_photo(auth_client, collection_id, item_id):
    fake_image = io.BytesIO(b"fake-image-data")
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", fake_image, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert "storage_key" in resp.json()


@pytest.mark.asyncio
async def test_upload_sets_first_as_hero(auth_client, collection_id, item_id):
    fake_image = io.BytesIO(b"fake-image-data")
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", fake_image, "image/jpeg")},
    )
    assert resp.json()["is_hero"] is True


@pytest.mark.asyncio
async def test_second_photo_not_hero(auth_client, collection_id, item_id):
    await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("first.jpg", io.BytesIO(b"data1"), "image/jpeg")},
    )
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("second.jpg", io.BytesIO(b"data2"), "image/jpeg")},
    )
    assert resp.json()["is_hero"] is False


@pytest.mark.asyncio
async def test_list_photos(auth_client, collection_id, item_id):
    await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("a.jpg", io.BytesIO(b"a"), "image/jpeg")},
    )
    await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("b.jpg", io.BytesIO(b"b"), "image/jpeg")},
    )
    resp = await auth_client.get(f"/collections/{collection_id}/items/{item_id}/photos")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_serve_photo(auth_client, collection_id, item_id):
    fake_image = io.BytesIO(b"fake-image-data")
    upload_resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", fake_image, "image/jpeg")},
    )
    storage_key = upload_resp.json()["storage_key"]
    resp = await auth_client.get(f"/photos/{storage_key}")
    assert resp.status_code == 200
    assert resp.content == b"fake-image-data"
