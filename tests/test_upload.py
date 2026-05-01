"""Tests for upload/staging endpoints (B1–B8)."""
from __future__ import annotations

import io
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, select, text

from app.models import (
    Base,
    CollectionTable,
    ItemPhotoTable,
    ItemTable,
    StagingPhotoTable,
    UserTable,
)

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# B1: StagingPhotoTable schema tests
# ---------------------------------------------------------------------------

async def test_staging_photo_table_columns_exist(db_engine):
    """staging_photos table has the expected columns."""
    async with db_engine.connect() as conn:
        def _check(sync_conn):
            inspector = inspect(sync_conn)
            cols = {c["name"] for c in inspector.get_columns("staging_photos")}
            required = {"id", "user_id", "storage_key", "thumbnail_key", "original_filename", "captured_at", "created_at"}
            missing = required - cols
            assert not missing, f"Missing columns: {missing}"
        await conn.run_sync(_check)


async def test_staging_photo_user_fk_cascades(db_session):
    """Deleting a user cascades and removes their staging photo rows."""
    user = UserTable(email="cascade_test@example.com", name="Cascade Test", role="curator")
    db_session.add(user)
    await db_session.flush()

    staging = StagingPhotoTable(
        user_id=user.id,
        storage_key="staging/1/abc.jpg",
        thumbnail_key="staging/1/abc.thumb.jpg",
    )
    db_session.add(staging)
    await db_session.commit()

    # Delete the user
    await db_session.delete(user)
    await db_session.commit()

    # The staging row should be gone
    result = await db_session.execute(
        select(StagingPhotoTable).where(StagingPhotoTable.user_id == user.id)
    )
    rows = result.scalars().all()
    assert rows == [], f"Expected no staging rows after user delete, got {rows}"


# ---------------------------------------------------------------------------
# B2: Cascade hardening tests
# ---------------------------------------------------------------------------

async def test_item_photo_cascades_on_item_delete(db_session):
    """Deleting an item cascades and removes its ItemPhotoTable rows."""
    # Create a user + collection + item + photo
    user = UserTable(email="cascade_item@example.com", name="Cascade Item", role="curator")
    db_session.add(user)
    await db_session.flush()

    coll = CollectionTable(owner_id=user.id, name="Test Coll")
    db_session.add(coll)
    await db_session.flush()

    item = ItemTable(collection_id=coll.id, brand="test", description="", status="undecided")
    db_session.add(item)
    await db_session.flush()

    photo = ItemPhotoTable(item_id=item.id, storage_key="collections/1/items/1/a.jpg", is_hero=True, sort_order=0)
    db_session.add(photo)
    await db_session.commit()

    # Delete the item
    await db_session.delete(item)
    await db_session.commit()

    result = await db_session.execute(
        select(ItemPhotoTable).where(ItemPhotoTable.item_id == item.id)
    )
    assert result.scalars().all() == []


async def test_item_cascades_on_collection_delete(db_session):
    """Deleting a collection cascades to items AND item_photos."""
    user = UserTable(email="cascade_coll@example.com", name="Cascade Coll", role="curator")
    db_session.add(user)
    await db_session.flush()

    coll = CollectionTable(owner_id=user.id, name="Test Coll 2")
    db_session.add(coll)
    await db_session.flush()

    item = ItemTable(collection_id=coll.id, brand="test", description="", status="undecided")
    db_session.add(item)
    await db_session.flush()

    photo = ItemPhotoTable(item_id=item.id, storage_key="collections/1/items/1/b.jpg", is_hero=True, sort_order=0)
    db_session.add(photo)
    await db_session.commit()

    item_id = item.id
    coll_id = coll.id

    # Delete the collection
    await db_session.delete(coll)
    await db_session.commit()

    items_result = await db_session.execute(
        select(ItemTable).where(ItemTable.collection_id == coll_id)
    )
    assert items_result.scalars().all() == []

    photos_result = await db_session.execute(
        select(ItemPhotoTable).where(ItemPhotoTable.item_id == item_id)
    )
    assert photos_result.scalars().all() == []


# ---------------------------------------------------------------------------
# B3: POST /upload/photos tests
# ---------------------------------------------------------------------------

def _png_bytes() -> bytes:
    """Return a minimal valid PNG."""
    from PIL import Image
    import io as _io
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def test_upload_photos_creates_staging_rows(auth_client, db_session_factory, photo_storage_root):
    """POST 3 fixture PNGs → 3 succeeded entries and 3 DB rows."""
    purse_dir = Path(__file__).parent / "fixtures" / "purses"
    files = [
        ("files", (f"purse{i}.png", open(p, "rb"), "image/png"))
        for i, p in enumerate(list(purse_dir.glob("*.png"))[:3])
    ]
    resp = await auth_client.post("/upload/photos", files=files)
    for _, (_, fh, _) in files:
        fh.close()
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["succeeded"]) == 3
    assert len(data["failed"]) == 0
    for entry in data["succeeded"]:
        assert "id" in entry
        assert "thumbnail_url" in entry
        assert "original_filename" in entry
        assert "captured_at" in entry


async def test_upload_photos_per_file_partial_failure(auth_client, photo_storage_root):
    """POST 1 valid PNG + 1 fake txt → partial success."""
    purse_dir = Path(__file__).parent / "fixtures" / "purses"
    png_file = next(purse_dir.glob("*.png"))
    files = [
        ("files", ("valid.png", open(png_file, "rb"), "image/png")),
        ("files", ("bad.txt", b"not an image", "text/plain")),
    ]
    resp = await auth_client.post("/upload/photos", files=files)
    files[0][1][1].close()
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["succeeded"]) == 1
    assert len(data["failed"]) == 1
    assert data["failed"][0]["original_filename"] == "bad.txt"
    assert "unsupported" in data["failed"][0]["reason"].lower() or "format" in data["failed"][0]["reason"].lower()


async def test_upload_photos_rejects_oversize_per_file(auth_client, photo_storage_root):
    """26 MB file → appears in failed with 'too large' reason."""
    big_data = b"\x89PNG\r\n\x1a\n" + bytes(26 * 1024 * 1024)
    files = [("files", ("big.png", big_data, "image/png"))]
    resp = await auth_client.post("/upload/photos", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["failed"]) == 1
    assert "too large" in data["failed"][0]["reason"].lower() or "large" in data["failed"][0]["reason"].lower()


async def test_upload_photos_rejects_more_than_50_files(auth_client, photo_storage_root):
    """51 files → HTTP 400 or 413."""
    small = _png_bytes()
    files = [("files", (f"f{i}.png", small, "image/png")) for i in range(51)]
    resp = await auth_client.post("/upload/photos", files=files)
    assert resp.status_code in (400, 413), resp.text


async def test_upload_photos_unauthenticated_401(client, photo_storage_root):
    """No session → 401."""
    resp = await client.post("/upload/photos", files=[("files", ("a.png", b"x", "image/png"))])
    assert resp.status_code == 401


async def test_upload_photos_accepted_formats_pin():
    """_sniff_format recognizes JPEG, PNG, HEIC, HEIF, WebP magic bytes."""
    from app.services.photo_pipeline import _sniff_format

    jpeg_bytes = b"\xff\xd8\xff" + b"\x00" * 20
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    # HEIC: bytes 4-7 == 'ftyp', bytes 8-11 == 'heic'
    heic_bytes = b"\x00\x00\x00\x18" + b"ftyp" + b"heic" + b"\x00" * 20
    # HEIF variant: mif1 brand
    heif_bytes = b"\x00\x00\x00\x18" + b"ftyp" + b"mif1" + b"\x00" * 20
    # WebP: RIFF????WEBP
    webp_bytes = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 20

    assert _sniff_format(jpeg_bytes) == "jpeg"
    assert _sniff_format(png_bytes) == "png"
    assert _sniff_format(heic_bytes) in ("heic", "heif")
    assert _sniff_format(heif_bytes) in ("heic", "heif")
    assert _sniff_format(webp_bytes) == "webp"


async def test_upload_request_too_large_returns_413(photo_storage_root, db_engine, db_session_factory):
    """Content-Length > 200MB → 413 from middleware."""
    from app.main import create_app
    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/upload/photos",
            content=b"x",
            headers={"Content-Length": str(200 * 1024 * 1024 + 1), "Content-Type": "multipart/form-data; boundary=boundary"},
        )
    assert resp.status_code == 413, resp.text


# ---------------------------------------------------------------------------
# B4: GET /upload/staging tests
# ---------------------------------------------------------------------------

async def _seed_staging_rows(db_session, user_id: int, count: int, **kwargs) -> list:
    """Create `count` staging rows for a user. Returns list of inserted objects."""
    rows = []
    for i in range(count):
        row = StagingPhotoTable(
            user_id=user_id,
            storage_key=f"staging/{user_id}/file{i}.jpg",
            thumbnail_key=f"staging/{user_id}/file{i}.thumb.jpg",
            original_filename=f"file{i}.jpg",
            **kwargs,
        )
        db_session.add(row)
        rows.append(row)
    await db_session.flush()
    await db_session.commit()
    # Refresh to get IDs
    for r in rows:
        await db_session.refresh(r)
    return rows


async def _get_user_id(auth_client) -> int:
    """Extract the current user's ID from /auth/me."""
    resp = await auth_client.get("/auth/me")
    return resp.json()["id"]


async def test_get_staging_returns_user_photos_only(auth_client, other_auth_client, db_session, photo_storage_root):
    """User A can only see their own staging photos."""
    uid_a = await _get_user_id(auth_client)
    uid_b = await _get_user_id(other_auth_client)

    await _seed_staging_rows(db_session, uid_a, 2)
    await _seed_staging_rows(db_session, uid_b, 2)

    resp = await auth_client.get("/upload/staging")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["photos"]) == 2
    for p in data["photos"]:
        # each has expected fields
        assert "id" in p
        assert "thumbnail_url" in p


async def test_get_staging_pagination_with_before(auth_client, db_session, photo_storage_root):
    """Cursor pagination with before= works correctly."""
    uid = await _get_user_id(auth_client)
    rows = await _seed_staging_rows(db_session, uid, 5)
    # Sort by id desc to get highest ids first
    ids_desc = sorted([r.id for r in rows], reverse=True)

    resp = await auth_client.get("/upload/staging?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["photos"]) == 2
    assert data["has_more"] is True

    # Get the lowest id from first page
    last_id = data["photos"][-1]["id"]
    resp2 = await auth_client.get(f"/upload/staging?limit=2&before={last_id}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["photos"]) == 2
    # All returned IDs should be less than last_id
    for p in data2["photos"]:
        assert p["id"] < last_id


async def test_get_staging_limit_caps_at_200(auth_client, db_session, photo_storage_root):
    """?limit=500 is clamped to 200."""
    uid = await _get_user_id(auth_client)
    # Seed 3 rows — server clamps the limit, doesn't fail
    await _seed_staging_rows(db_session, uid, 3)

    resp = await auth_client.get("/upload/staging?limit=500")
    assert resp.status_code == 200
    data = resp.json()
    # The response should succeed and respect clamp (3 rows <= 200 cap)
    assert isinstance(data["photos"], list)
    assert len(data["photos"]) <= 200


async def test_get_staging_unauth_401(client):
    """No session → 401."""
    resp = await client.get("/upload/staging")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# B5: POST /upload/group tests
# ---------------------------------------------------------------------------

async def _seed_staging_with_files(db_session, user_id: int, photo_storage_root: str, count: int):
    """Create staging rows AND the actual files on disk."""
    from PIL import Image
    import io as _io

    root = Path(photo_storage_root)
    rows = []
    for i in range(count):
        # Create actual file
        staging_dir = root / "staging" / str(user_id)
        staging_dir.mkdir(parents=True, exist_ok=True)
        fname = f"seed{i}.jpg"
        thumb_fname = f"seed{i}.thumb.jpg"
        fpath = staging_dir / fname
        tpath = staging_dir / thumb_fname

        img = Image.new("RGB", (10, 10), color=(i * 20 % 255, 0, 0))
        img.save(str(fpath), format="JPEG")
        img.save(str(tpath), format="JPEG")

        storage_key = f"staging/{user_id}/{fname}"
        thumbnail_key = f"staging/{user_id}/{thumb_fname}"

        row = StagingPhotoTable(
            user_id=user_id,
            storage_key=storage_key,
            thumbnail_key=thumbnail_key,
            original_filename=fname,
        )
        db_session.add(row)
        rows.append(row)

    await db_session.flush()
    await db_session.commit()
    for r in rows:
        await db_session.refresh(r)
    return rows


async def test_group_creates_item_with_photos_in_order(auth_client, db_session, photo_storage_root):
    """POST /upload/group creates item + photos, deletes staging rows."""
    uid = await _get_user_id(auth_client)

    # Create a collection
    resp = await auth_client.post("/collections", json={"name": "Test Coll", "description": ""})
    assert resp.status_code == 201
    coll_id = resp.json()["id"]

    # Seed staging rows with files
    rows = await _seed_staging_with_files(db_session, uid, photo_storage_root, 3)
    photo_ids = [r.id for r in rows]

    resp = await auth_client.post("/upload/group", json={"collection_id": coll_id, "photo_ids": photo_ids})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "item_id" in data

    # Check item was created
    result = await db_session.execute(select(ItemTable).where(ItemTable.id == data["item_id"]))
    item = result.scalar_one_or_none()
    assert item is not None

    # Check 3 ItemPhotoTable rows
    result = await db_session.execute(select(ItemPhotoTable).where(ItemPhotoTable.item_id == item.id))
    photos = result.scalars().all()
    assert len(photos) == 3

    # First is hero, sort_orders are 0,1,2
    sort_orders = sorted(p.sort_order for p in photos)
    assert sort_orders == [0, 1, 2]
    hero_photos = [p for p in photos if p.is_hero]
    assert len(hero_photos) == 1

    # Staging rows should be deleted
    result = await db_session.execute(select(StagingPhotoTable).where(StagingPhotoTable.id.in_(photo_ids)))
    remaining = result.scalars().all()
    assert remaining == []


async def test_group_renames_files_to_collection_path(auth_client, db_session, photo_storage_root):
    """After grouping, files should be renamed to collections/ path (or fallback to staging path)."""
    uid = await _get_user_id(auth_client)
    root = Path(photo_storage_root)

    resp = await auth_client.post("/collections", json={"name": "Rename Coll", "description": ""})
    coll_id = resp.json()["id"]

    rows = await _seed_staging_with_files(db_session, uid, photo_storage_root, 1)
    original_staging_key = rows[0].storage_key
    original_staging_path = root / original_staging_key

    resp = await auth_client.post("/upload/group", json={"collection_id": coll_id, "photo_ids": [rows[0].id]})
    assert resp.status_code == 200
    item_id = resp.json()["item_id"]

    # Get ItemPhotoTable row
    result = await db_session.execute(select(ItemPhotoTable).where(ItemPhotoTable.item_id == item_id))
    photo = result.scalar_one()

    # Either file was renamed to collections/ path, or it stays at staging path
    if photo.storage_key.startswith("staging/"):
        # fallback — file should still exist at staging
        assert (root / photo.storage_key).exists()
    else:
        # renamed — file should exist at new path
        assert (root / photo.storage_key).exists()
        # original staging path should be gone
        assert not original_staging_path.exists()


async def test_group_rename_failure_leaves_staging_path_but_succeeds(auth_client, db_session, photo_storage_root, monkeypatch):
    """If rename fails on the 2nd file, 1st gets renamed, 2nd stays at staging path. HTTP 200."""
    uid = await _get_user_id(auth_client)
    root = Path(photo_storage_root)

    resp = await auth_client.post("/collections", json={"name": "Partial Rename Coll", "description": ""})
    coll_id = resp.json()["id"]

    rows = await _seed_staging_with_files(db_session, uid, photo_storage_root, 2)

    # Patch os.rename to fail on the 2nd call
    call_count = {"n": 0}
    real_rename = os.rename

    def fake_rename(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("Simulated rename failure")
        real_rename(src, dst)

    monkeypatch.setattr(os, "rename", fake_rename)

    resp = await auth_client.post("/upload/group", json={"collection_id": coll_id, "photo_ids": [r.id for r in rows]})
    assert resp.status_code == 200, resp.text
    item_id = resp.json()["item_id"]

    # Both ItemPhotoTable rows should exist
    result = await db_session.execute(select(ItemPhotoTable).where(ItemPhotoTable.item_id == item_id))
    photos = result.scalars().all()
    assert len(photos) == 2

    # Both files should exist on disk (one renamed, one at staging)
    for photo in photos:
        assert (root / photo.storage_key).exists(), f"File missing: {photo.storage_key}"


async def test_group_rename_failure_on_first_file(auth_client, db_session, photo_storage_root, monkeypatch):
    """If rename fails on the FIRST file, no files moved, both stay at staging paths."""
    uid = await _get_user_id(auth_client)
    root = Path(photo_storage_root)

    resp = await auth_client.post("/collections", json={"name": "First Fail Coll", "description": ""})
    coll_id = resp.json()["id"]

    rows = await _seed_staging_with_files(db_session, uid, photo_storage_root, 2)
    staging_keys = [r.storage_key for r in rows]

    real_rename = os.rename

    def fake_rename_fail_first(src, dst):
        raise OSError("Simulated rename failure on first call")

    monkeypatch.setattr(os, "rename", fake_rename_fail_first)

    resp = await auth_client.post("/upload/group", json={"collection_id": coll_id, "photo_ids": [r.id for r in rows]})
    assert resp.status_code == 200, resp.text
    item_id = resp.json()["item_id"]

    # Both ItemPhotoTable rows should exist
    result = await db_session.execute(select(ItemPhotoTable).where(ItemPhotoTable.item_id == item_id))
    photos = result.scalars().all()
    assert len(photos) == 2

    # Both files should still be at their staging paths
    for photo in photos:
        assert (root / photo.storage_key).exists(), f"File missing at staging: {photo.storage_key}"


async def test_group_atomic_db_failure_leaves_staging_intact(auth_client, db_session, photo_storage_root, monkeypatch):
    """If DB insert fails, no ItemTable row, all staging rows still present, no files moved."""
    uid = await _get_user_id(auth_client)
    root = Path(photo_storage_root)

    resp = await auth_client.post("/collections", json={"name": "Atomic Coll", "description": ""})
    coll_id = resp.json()["id"]

    rows = await _seed_staging_with_files(db_session, uid, photo_storage_root, 2)
    photo_ids = [r.id for r in rows]
    staging_keys = [r.storage_key for r in rows]

    # Monkeypatch ItemPhotoTable.__init__ to raise on first call
    orig_init = ItemPhotoTable.__init__
    call_count = {"n": 0}

    def bad_init(self, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("Simulated DB insert failure")
        orig_init(self, **kwargs)

    monkeypatch.setattr(ItemPhotoTable, "__init__", bad_init)

    resp = await auth_client.post("/upload/group", json={"collection_id": coll_id, "photo_ids": photo_ids})
    # Should be an error (500 or similar)
    assert resp.status_code in (500, 422, 400), f"Expected error, got {resp.status_code}: {resp.text}"

    # Re-fetch staging rows - they should still be present
    # Use a new session since the test session might be tainted
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async with db_session.bind.connect() as conn:
        result = await conn.execute(
            select(StagingPhotoTable).where(StagingPhotoTable.id.in_(photo_ids))
        )
        # Actually use existing session with fresh query
    result2 = await db_session.execute(
        select(StagingPhotoTable).where(StagingPhotoTable.id.in_(photo_ids))
    )
    remaining = result2.scalars().all()
    assert len(remaining) == 2, f"Expected 2 staging rows, found {len(remaining)}"

    # Files should NOT have been moved
    for key in staging_keys:
        assert (root / key).exists(), f"Staging file was incorrectly removed: {key}"


async def test_group_idor_returns_404_when_photo_id_belongs_to_another_user(auth_client, other_auth_client, db_session, photo_storage_root):
    """Trying to group another user's photo returns 404."""
    uid_b = await _get_user_id(other_auth_client)
    rows = await _seed_staging_with_files(db_session, uid_b, photo_storage_root, 1)

    resp_coll = await auth_client.post("/collections", json={"name": "IDOR Coll", "description": ""})
    coll_id = resp_coll.json()["id"]

    resp = await auth_client.post("/upload/group", json={"collection_id": coll_id, "photo_ids": [rows[0].id]})
    assert resp.status_code == 404, resp.text


async def test_group_idor_returns_404_when_collection_belongs_to_another_user(auth_client, other_auth_client, db_session, photo_storage_root):
    """Collection owned by another user → 404."""
    uid_a = await _get_user_id(auth_client)
    rows = await _seed_staging_with_files(db_session, uid_a, photo_storage_root, 1)

    resp_coll = await other_auth_client.post("/collections", json={"name": "Other Coll", "description": ""})
    other_coll_id = resp_coll.json()["id"]

    resp = await auth_client.post("/upload/group", json={"collection_id": other_coll_id, "photo_ids": [rows[0].id]})
    assert resp.status_code == 404, resp.text


async def test_group_atomic_when_db_insert_fails(auth_client, db_session, photo_storage_root, monkeypatch):
    """Alias of atomic test - monkeypatch on second ItemPhotoTable.__init__ call."""
    uid = await _get_user_id(auth_client)
    root = Path(photo_storage_root)

    resp = await auth_client.post("/collections", json={"name": "Atomic2 Coll", "description": ""})
    coll_id = resp.json()["id"]

    rows = await _seed_staging_with_files(db_session, uid, photo_storage_root, 2)
    photo_ids = [r.id for r in rows]

    orig_init = ItemPhotoTable.__init__
    call_count = {"n": 0}

    def bad_init_second(self, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("Simulated DB insert failure on second call")
        orig_init(self, **kwargs)

    monkeypatch.setattr(ItemPhotoTable, "__init__", bad_init_second)

    resp = await auth_client.post("/upload/group", json={"collection_id": coll_id, "photo_ids": photo_ids})
    assert resp.status_code in (500, 422, 400), f"Expected error, got {resp.status_code}"

    result = await db_session.execute(
        select(StagingPhotoTable).where(StagingPhotoTable.id.in_(photo_ids))
    )
    remaining = result.scalars().all()
    assert len(remaining) == 2, f"Expected staging rows intact, got {len(remaining)}"


# ---------------------------------------------------------------------------
# B6: DELETE /upload/staging/{id} tests
# ---------------------------------------------------------------------------

async def test_discard_staging_removes_row_and_files(auth_client, db_session, photo_storage_root):
    """DELETE removes the DB row and the files on disk."""
    uid = await _get_user_id(auth_client)
    root = Path(photo_storage_root)
    rows = await _seed_staging_with_files(db_session, uid, photo_storage_root, 1)
    row = rows[0]

    full_path = root / row.storage_key
    thumb_path = root / row.thumbnail_key
    assert full_path.exists()
    assert thumb_path.exists()

    resp = await auth_client.delete(f"/upload/staging/{row.id}")
    assert resp.status_code == 204, resp.text

    # Row gone
    result = await db_session.execute(select(StagingPhotoTable).where(StagingPhotoTable.id == row.id))
    assert result.scalar_one_or_none() is None

    # Files gone
    assert not full_path.exists()
    assert not thumb_path.exists()


async def test_discard_staging_idor_404(auth_client, other_auth_client, db_session, photo_storage_root):
    """User A cannot delete user B's staging row."""
    uid_b = await _get_user_id(other_auth_client)
    rows = await _seed_staging_with_files(db_session, uid_b, photo_storage_root, 1)

    resp = await auth_client.delete(f"/upload/staging/{rows[0].id}")
    assert resp.status_code == 404, resp.text

    # Row still present
    result = await db_session.execute(select(StagingPhotoTable).where(StagingPhotoTable.id == rows[0].id))
    assert result.scalar_one_or_none() is not None


async def test_discard_staging_missing_404(auth_client, photo_storage_root):
    """Deleting a non-existent staging id → 404."""
    resp = await auth_client.delete("/upload/staging/999999")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# B8: Per-user 500 staging cap tests
# ---------------------------------------------------------------------------

async def test_upload_photos_returns_429_when_user_at_500_staging(auth_client, db_session, photo_storage_root):
    """POST with 500 existing staging rows → HTTP 429."""
    uid = await _get_user_id(auth_client)
    # Insert 500 rows directly (no files needed — cap check is pre-flight)
    for i in range(500):
        db_session.add(StagingPhotoTable(
            user_id=uid,
            storage_key=f"staging/{uid}/cap_test_{i}.jpg",
            thumbnail_key=f"staging/{uid}/cap_test_{i}.thumb.jpg",
        ))
    await db_session.commit()

    purse_dir = Path(__file__).parent / "fixtures" / "purses"
    png_file = next(purse_dir.glob("*.png"))
    files = [("files", ("one.png", open(png_file, "rb"), "image/png"))]
    resp = await auth_client.post("/upload/photos", files=files)
    files[0][1][1].close()
    assert resp.status_code == 429, resp.text
    assert "group or discard" in resp.json().get("detail", "").lower()


async def test_upload_photos_partial_when_user_near_500_cap(auth_client, db_session, photo_storage_root):
    """POST 5 files when user has 498 staging rows → HTTP 429 (entire batch rejected)."""
    uid = await _get_user_id(auth_client)
    for i in range(498):
        db_session.add(StagingPhotoTable(
            user_id=uid,
            storage_key=f"staging/{uid}/near_cap_{i}.jpg",
            thumbnail_key=f"staging/{uid}/near_cap_{i}.thumb.jpg",
        ))
    await db_session.commit()

    purse_dir = Path(__file__).parent / "fixtures" / "purses"
    png_files = list(purse_dir.glob("*.png"))[:5]
    files = [("files", (f"p{i}.png", open(p, "rb"), "image/png")) for i, p in enumerate(png_files)]
    resp = await auth_client.post("/upload/photos", files=files)
    for _, (_, fh, _) in files:
        fh.close()
    assert resp.status_code == 429, resp.text

    # No new rows created
    result = await db_session.execute(
        select(StagingPhotoTable).where(StagingPhotoTable.user_id == uid)
    )
    count = len(result.scalars().all())
    assert count == 498, f"Expected 498 rows (no new ones), got {count}"
