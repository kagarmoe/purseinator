from __future__ import annotations

import io

import pytest
from PIL import Image


def _jpeg_bytes(color: tuple[int, int, int] = (200, 100, 50), size: tuple[int, int] = (100, 80)) -> bytes:
    """Return minimal valid JPEG bytes."""
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="JPEG")
    return buf.getvalue()


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
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
    )
    assert resp.status_code == 201
    assert "storage_key" in resp.json()


@pytest.mark.asyncio
async def test_upload_sets_first_as_hero(auth_client, collection_id, item_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
    )
    assert resp.json()["is_hero"] is True


@pytest.mark.asyncio
async def test_second_photo_not_hero(auth_client, collection_id, item_id):
    await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("first.jpg", io.BytesIO(_jpeg_bytes(color=(10, 20, 30))), "image/jpeg")},
    )
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("second.jpg", io.BytesIO(_jpeg_bytes(color=(40, 50, 60))), "image/jpeg")},
    )
    assert resp.json()["is_hero"] is False


@pytest.mark.asyncio
async def test_list_photos(auth_client, collection_id, item_id):
    await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("a.jpg", io.BytesIO(_jpeg_bytes(color=(10, 20, 30))), "image/jpeg")},
    )
    await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("b.jpg", io.BytesIO(_jpeg_bytes(color=(40, 50, 60))), "image/jpeg")},
    )
    resp = await auth_client.get(f"/collections/{collection_id}/items/{item_id}/photos")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_upload_photo_missing_item_returns_404(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/99999/photos",
        files={"file": ("bag.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_photos_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.get(f"/collections/{collection_id}/items/{item_id}/photos")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_serve_photo(auth_client, collection_id, item_id, photo_storage_root):
    upload_resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
    )
    storage_key = upload_resp.json()["storage_key"]
    resp = await auth_client.get(f"/photos/{storage_key}")
    assert resp.status_code == 200
    # Content is a valid JPEG (pipeline converts to JPEG)
    assert resp.content[:3] == b"\xff\xd8\xff"


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------

def _make_jpeg_with_exif_bytes(
    width: int = 100,
    height: int = 100,
    orientation: int = 1,
    date_time_original: str | None = None,
) -> bytes:
    """Build a JPEG with optional EXIF tags."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    exif = img.getexif()
    if orientation != 1:
        exif[0x0112] = orientation
    if date_time_original:
        exif[36867] = date_time_original
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_stores_thumbnail(auth_client, collection_id, item_id, photo_storage_root):
    """Upload a JPEG → thumbnail file exists on disk and thumbnail_key is in response."""
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", io.BytesIO(_jpeg_bytes(size=(200, 150))), "image/jpeg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "thumbnail_key" in data
    assert data["thumbnail_key"] is not None
    from pathlib import Path
    thumb_path = Path(photo_storage_root) / data["thumbnail_key"]
    assert thumb_path.exists(), f"Thumbnail file not found at {thumb_path}"


@pytest.mark.asyncio
async def test_upload_thumbnail_dimensions(auth_client, collection_id, item_id, photo_storage_root):
    """Uploaded 1200×800 image → thumbnail is at most 600×600."""
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("large.jpg", io.BytesIO(_jpeg_bytes(size=(1200, 800))), "image/jpeg")},
    )
    data = resp.json()
    from pathlib import Path
    thumb_path = Path(photo_storage_root) / data["thumbnail_key"]
    thumb_img = Image.open(thumb_path)
    w, h = thumb_img.size
    assert w <= 600 and h <= 600, f"Thumbnail {w}×{h} exceeds 600×600"


@pytest.mark.asyncio
async def test_upload_storage_key_is_uuid_jpg(auth_client, collection_id, item_id):
    """storage_key ends with a UUID-style hex + .jpg; no original filename in path."""
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("my-bag-photo.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
    )
    storage_key = resp.json()["storage_key"]
    assert storage_key.endswith(".jpg"), f"storage_key should end with .jpg: {storage_key}"
    assert "my-bag-photo" not in storage_key, "Original filename must not appear in storage_key"


@pytest.mark.asyncio
async def test_upload_captured_at_extracted(auth_client, collection_id, item_id):
    """Upload image with DateTimeOriginal EXIF → captured_at is populated in response."""
    data = _make_jpeg_with_exif_bytes(date_time_original="2026:04:30 18:42:00")
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("dated.jpg", io.BytesIO(data), "image/jpeg")},
    )
    assert resp.status_code == 201
    captured_at = resp.json().get("captured_at")
    assert captured_at is not None, "captured_at should be populated from EXIF"
    assert "2026" in captured_at


@pytest.mark.asyncio
async def test_upload_captured_at_none_without_exif(auth_client, collection_id, item_id):
    """Upload plain JPEG with no EXIF → captured_at is None."""
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("plain.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json().get("captured_at") is None


@pytest.mark.asyncio
async def test_upload_heic_converted_to_jpeg(auth_client, collection_id, item_id, photo_storage_root):
    """HEIC upload → stored file is JPEG, storage_key ends in .jpg."""
    import pillow_heif
    img = Image.new("RGB", (64, 64), color=(255, 128, 0))
    heif_file = pillow_heif.from_pillow(img)
    buf = io.BytesIO()
    heif_file.save(buf, format="HEIF")
    heic_bytes = buf.getvalue()

    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("photo.heic", io.BytesIO(heic_bytes), "image/heic")},
    )
    assert resp.status_code == 201
    storage_key = resp.json()["storage_key"]
    assert storage_key.endswith(".jpg"), "HEIC should be stored as .jpg"
    from pathlib import Path
    full_path = Path(photo_storage_root) / storage_key
    content = full_path.read_bytes()
    assert content[:3] == b"\xff\xd8\xff", "Stored file is not a valid JPEG"


@pytest.mark.asyncio
async def test_upload_unsupported_format_returns_415(auth_client, collection_id, item_id):
    """Uploading a non-image text file → 415."""
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_too_large_returns_413(auth_client, collection_id, item_id):
    """Uploading a file >25 MB → 413."""
    large = b"\xff\xd8\xff" + b"x" * (25 * 1024 * 1024 + 10)
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("big.jpg", io.BytesIO(large), "image/jpeg")},
    )
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# GET /photos/{key}/thumb endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_serve_thumbnail_returns_jpeg(auth_client, collection_id, item_id):
    """GET /photos/{storage_key}/thumb returns the thumbnail JPEG."""
    upload_resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", io.BytesIO(_jpeg_bytes(size=(200, 150))), "image/jpeg")},
    )
    storage_key = upload_resp.json()["storage_key"]
    resp = await auth_client.get(f"/photos/{storage_key}/thumb")
    assert resp.status_code == 200
    # Response is a valid JPEG
    assert resp.content[:3] == b"\xff\xd8\xff", "Thumbnail response is not a JPEG"


@pytest.mark.asyncio
async def test_serve_thumbnail_dimensions_le_600(auth_client, collection_id, item_id):
    """Thumbnail served by the endpoint is ≤ 600×600."""
    upload_resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("large.jpg", io.BytesIO(_jpeg_bytes(size=(1200, 900))), "image/jpeg")},
    )
    storage_key = upload_resp.json()["storage_key"]
    resp = await auth_client.get(f"/photos/{storage_key}/thumb")
    assert resp.status_code == 200
    thumb_img = Image.open(io.BytesIO(resp.content))
    w, h = thumb_img.size
    assert w <= 600 and h <= 600, f"Served thumbnail {w}×{h} exceeds 600×600"


@pytest.mark.asyncio
async def test_serve_thumbnail_404_for_missing_key(auth_client):
    """GET /photos/nonexistent-key.jpg/thumb → 404."""
    resp = await auth_client.get("/photos/collections/0/items/0/deadbeef.jpg/thumb")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_serve_thumbnail_fallback_to_full_res(auth_client, collection_id, item_id, photo_storage_root):
    """
    If the thumbnail file is missing (legacy row), the endpoint falls back to
    serving the full-resolution image rather than 404.
    """
    # Upload normally to create a valid row + files
    upload_resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", io.BytesIO(_jpeg_bytes(size=(200, 150))), "image/jpeg")},
    )
    storage_key = upload_resp.json()["storage_key"]
    thumbnail_key = upload_resp.json()["thumbnail_key"]

    # Manually delete the thumbnail file to simulate a legacy row
    from pathlib import Path
    thumb_path = Path(photo_storage_root) / thumbnail_key
    thumb_path.unlink()

    # Endpoint should fall back to full-res, not 404
    resp = await auth_client.get(f"/photos/{storage_key}/thumb")
    assert resp.status_code == 200
    assert resp.content[:3] == b"\xff\xd8\xff", "Fallback response is not a JPEG"


@pytest.mark.asyncio
async def test_serve_thumbnail_legacy_row_null_thumbnail_key(
    auth_client, collection_id, item_id, photo_storage_root, db_session
):
    """
    Legacy rows with thumbnail_key IS NULL fall back to serving the full-res image.

    This exercises the case where a row was created before the thumbnail pipeline
    was wired in (plan 1 rows), so thumbnail_key is NULL rather than a file that
    was deleted.
    """
    from pathlib import Path
    from app.models import ItemPhotoTable

    # Create a full-res image file on disk to serve as fallback
    full_key = f"collections/{collection_id}/items/{item_id}/legacy_row.jpg"
    full_path = Path(photo_storage_root) / full_key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(_jpeg_bytes())

    # Insert an ItemPhotoTable row directly with thumbnail_key=None
    row = ItemPhotoTable(
        item_id=item_id,
        storage_key=full_key,
        thumbnail_key=None,  # legacy row — no thumbnail was ever generated
        is_hero=False,
        sort_order=99,
        captured_at=None,
    )
    db_session.add(row)
    await db_session.commit()

    # The thumb endpoint should fall back to the full-res file
    resp = await auth_client.get(f"/photos/{full_key}/thumb")
    assert resp.status_code == 200
    assert resp.content[:3] == b"\xff\xd8\xff", "Fallback full-res response is not a JPEG"
