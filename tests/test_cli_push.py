from __future__ import annotations

import io
import json

import pytest

from app.cli_client import push_collection


@pytest.fixture
async def operator_client(db_engine, db_session_factory, photo_storage_root):
    """Authenticated client with operator role for push tests."""
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app

    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/magic-link", json={"email": "kim@example.com"})
        token = resp.json()["token"]
        resp = await ac.get(f"/auth/verify?token={token}")
        session_id = resp.json()["session_id"]
        ac.cookies.set("session_id", session_id)
        yield ac


@pytest.mark.asyncio
async def test_push_creates_collection_and_items(operator_client, tmp_path):
    # Create fake photo files
    for name in ("IMG_002.jpg", "IMG_003.jpg", "IMG_005.jpg"):
        (tmp_path / name).write_bytes(b"fake-image-data")

    manifest = {
        "source_dir": str(tmp_path),
        "groups": [
            {"photos": ["IMG_002.jpg", "IMG_003.jpg"]},
            {"photos": ["IMG_005.jpg"]},
        ],
    }

    result = await push_collection(
        operator_client, manifest, collection_name="Push Test"
    )
    assert result["items_created"] == 2
    assert result["photos_uploaded"] == 3


@pytest.mark.asyncio
async def test_push_items_have_photos(operator_client, tmp_path):
    (tmp_path / "bag.jpg").write_bytes(b"photo-bytes")

    manifest = {
        "source_dir": str(tmp_path),
        "groups": [{"photos": ["bag.jpg"]}],
    }

    result = await push_collection(
        operator_client, manifest, collection_name="Photo Check"
    )
    collection_id = result["collection_id"]

    resp = await operator_client.get(f"/collections/{collection_id}/items")
    items = resp.json()
    assert len(items) == 1

    item_id = items[0]["id"]
    resp = await operator_client.get(
        f"/collections/{collection_id}/items/{item_id}/photos"
    )
    photos = resp.json()
    assert len(photos) == 1
    assert photos[0]["is_hero"] is True
