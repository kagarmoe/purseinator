from __future__ import annotations

import importlib.util
import io

import pytest
from PIL import Image


def _jpeg_bytes(color: tuple[int, int, int] = (200, 100, 50)) -> bytes:
    """Return minimal valid JPEG bytes."""
    buf = io.BytesIO()
    Image.new("RGB", (100, 80), color=color).save(buf, format="JPEG")
    return buf.getvalue()

numpy_available = importlib.util.find_spec("numpy") is not None
skip_no_gpu = pytest.mark.skipif(
    not numpy_available,
    reason="requires gpu extras: pip install -e '.[gpu]'"
)


@pytest.mark.asyncio
async def test_full_workflow(auth_client, photo_storage_root):
    """End-to-end: create collection -> add items with photos -> rank -> verify sorted."""
    # 1. Create collection
    resp = await auth_client.post(
        "/collections", json={"name": "Integration Test", "description": "Full workflow"}
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]

    # 2. Add 4 items with photos
    item_ids = []
    for brand in ("Coach", "Gucci", "Prada", "Chanel"):
        resp = await auth_client.post(
            f"/collections/{cid}/items", json={"brand": brand}
        )
        assert resp.status_code == 201
        item_id = resp.json()["id"]
        item_ids.append(item_id)

        # Upload a photo for each
        resp = await auth_client.post(
            f"/collections/{cid}/items/{item_id}/photos",
            files={"file": (f"{brand}.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
        )
        assert resp.status_code == 201
        assert resp.json()["is_hero"] is True

    # 3. Get initial ranking — all should be at 1500
    resp = await auth_client.get(f"/collections/{cid}/ranking")
    assert resp.status_code == 200
    ranked = resp.json()
    assert len(ranked) == 4
    assert all(r["rating"] == 1500.0 for r in ranked)

    # 4. Do 5 comparisons
    for _ in range(5):
        resp = await auth_client.get(f"/collections/{cid}/ranking/next")
        assert resp.status_code == 200
        pair = resp.json()
        assert pair["item_a"]["id"] != pair["item_b"]["id"]
        assert pair["info_level"] in ("photos_only", "brand", "condition", "price")

        resp = await auth_client.post(
            f"/collections/{cid}/ranking/compare",
            json={
                "item_a_id": pair["item_a"]["id"],
                "item_b_id": pair["item_b"]["id"],
                "winner_id": pair["item_a"]["id"],
                "info_level_shown": pair["info_level"],
            },
        )
        assert resp.status_code == 201

    # 5. Verify ranking changed and is sorted
    resp = await auth_client.get(f"/collections/{cid}/ranking")
    ranked = resp.json()
    ratings = [r["rating"] for r in ranked]
    assert ratings == sorted(ratings, reverse=True)
    assert not all(r == 1500.0 for r in ratings)

    # 6. Verify items have photos
    for item in ranked:
        resp = await auth_client.get(
            f"/collections/{cid}/items/{item['id']}/photos"
        )
        assert resp.status_code == 200
        photos = resp.json()
        assert len(photos) >= 1

    # 7. Update an item status
    resp = await auth_client.patch(
        f"/collections/{cid}/items/{ranked[0]['id']}",
        json={"status": "keeper"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "keeper"


@pytest.mark.asyncio
async def test_auth_flow(db_client):
    """Test complete auth cycle: magic link -> verify -> me -> logout -> rejected."""
    # Request magic link
    resp = await db_client.post("/auth/magic-link", json={"email": "test@example.com"})
    assert resp.status_code == 200
    token = resp.json()["token"]

    # Verify
    resp = await db_client.get(f"/auth/verify?token={token}")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Access /me
    db_client.cookies.set("session_id", session_id)
    resp = await db_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"

    # Logout
    resp = await db_client.post("/auth/logout")
    assert resp.status_code == 200

    # Session should be dead
    resp = await db_client.get("/auth/me")
    assert resp.status_code == 401


@skip_no_gpu
@pytest.mark.asyncio
async def test_ingest_and_push_workflow(auth_client, tmp_path, photo_storage_root):
    """Test CLI workflow: ingest photos -> push to server -> verify items exist."""
    import json
    import numpy as np
    import cv2

    from app.ingest.card_detector import is_delimiter_card
    from app.ingest.grouper import group_photos
    from app.cli_client import push_collection

    # Simulate photo files: card, bag, bag, card, bag
    for name, is_green in [
        ("IMG_001.jpg", True),
        ("IMG_002.jpg", False),
        ("IMG_003.jpg", False),
        ("IMG_004.jpg", True),
        ("IMG_005.jpg", False),
    ]:
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        if is_green:
            img[:, :] = [0, 255, 0]
        else:
            img[:, :] = [50, 100, 150]
        cv2.imwrite(str(tmp_path / name), img)

    # Run card detection
    files = sorted(tmp_path.glob("*.jpg"))
    flags = [is_delimiter_card(cv2.imread(str(f))) for f in files]
    assert flags == [True, False, False, True, False]

    # Group photos
    groups = group_photos([f.name for f in files], flags)
    assert len(groups) == 2

    # Build manifest and push
    manifest = {
        "source_dir": str(tmp_path),
        "groups": [{"photos": g} for g in groups],
    }

    result = await push_collection(auth_client, manifest, collection_name="Ingest Test")
    assert result["items_created"] == 2
    assert result["photos_uploaded"] == 3

    # Verify on server
    cid = result["collection_id"]
    resp = await auth_client.get(f"/collections/{cid}/items")
    assert len(resp.json()) == 2
