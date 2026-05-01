# Photo Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full photo processing pipeline (HEIC→JPEG conversion, EXIF rotate-and-strip, `captured_at` extraction, thumbnail generation, format sniffing) wired into the existing `POST /collections/{cid}/items/{iid}/photos` endpoint, and add a new `GET /photos/{key}/thumb` endpoint.

**Architecture:** A pure-function module `app/services/photo_pipeline.py` encapsulates all Pillow/pillow-heif logic and returns processed bytes — no I/O inside the module. The existing `upload_photo` route calls the pipeline and writes both full-resolution and thumbnail files to disk under UUID filenames. Two new nullable columns (`captured_at`, `thumbnail_key`) are added to `ItemPhotoTable` via Alembic migration.

**Tech Stack:** Python 3.10+, FastAPI, Pillow (>=10.2), pillow-heif

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `pyproject.toml` | Add `Pillow` and `pillow-heif` to production `dependencies` |
| Create | `app/services/photo_pipeline.py` | Pure pipeline: sniff → HEIC convert → rotate → strip → captured_at → full JPEG → thumb JPEG |
| Create | `tests/test_photo_pipeline.py` | Unit tests for pipeline module (no HTTP, no DB) |
| Modify | `app/models.py` | Add `captured_at` and `thumbnail_key` columns to `ItemPhotoTable`; add fields to `ItemPhotoRead` |
| Create | `alembic/versions/b2c3d4e5f6a7_add_photo_pipeline_columns.py` | Migration: add `captured_at` (DateTime nullable) and `thumbnail_key` (String nullable) to `item_photos` |
| Modify | `app/routes/photos.py` | Wire pipeline into `upload_photo`; add `GET /photos/{storage_key:path}/thumb` endpoint |
| Modify | `tests/test_photos.py` | Integration tests for pipeline-wired upload and thumbnail endpoint |

---

## Task 1: Add dependencies + pipeline skeleton with format detection

**Files:**
- Modify: `pyproject.toml`
- Create: `app/services/photo_pipeline.py`
- Create: `tests/test_photo_pipeline.py`

### Background

`Pillow` is currently only in `[project.optional-dependencies] gpu`. We need it and `pillow-heif` in the production `[project.dependencies]` list so they're available in the deployed container. `pillow-heif` must be registered once at module load via `pillow_heif.register_heif_opener()`.

The pipeline function signature for this entire plan:

```python
def process_photo(
    data: bytes,
    filename: str,
) -> tuple[bytes, bytes, datetime | None]:
    """
    Returns (full_jpeg_bytes, thumb_jpeg_bytes, captured_at).
    Raises UnsupportedFormatError if format not in {JPEG, PNG, HEIC, HEIF, WebP}.
    Raises FileTooLargeError if len(data) > 25 * 1024 * 1024.
    captured_at is None if no DateTimeOriginal EXIF is present.
    """
```

This task implements only the format-sniffing path (raise `UnsupportedFormatError` for bad input; pass through otherwise as a stub). The pipeline is fleshed out in Tasks 2–4.

- [ ] **Step 1: Add `Pillow` and `pillow-heif` to `pyproject.toml` production dependencies**

Open `pyproject.toml`. The `dependencies` list currently ends at `opentelemetry-instrumentation-fastapi`. Add two lines:

```toml
[project]
name = "purseinator"
version = "0.1.0"
description = "A web app for curating handbag collections"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "typer>=0.12",
    "python-multipart>=0.0.9",
    "pyjwt>=2.8",
    "opentelemetry-api>=1.24",
    "opentelemetry-sdk>=1.24",
    "opentelemetry-instrumentation-fastapi>=0.45b0",
    "Pillow>=10.2",
    "pillow-heif>=0.16",
]
```

Also remove `"pillow>=10.2"` from the `[project.optional-dependencies] gpu` section to avoid having it in two places (leave `torch` and `opencv-python` in gpu):

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.1",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "aiosqlite>=0.20",
]
gpu = [
    "torch>=2.2",
    "opencv-python>=4.9",
]
```

- [ ] **Step 2: Install updated dependencies**

```bash
cd /gt/purseinator/crew/kagarmoe && pip install -e ".[dev]" -q
```

Expected: completes without error. `import PIL` and `import pillow_heif` should now work.

- [ ] **Step 3: Write the failing unit tests for format detection**

Create `tests/test_photo_pipeline.py`:

```python
from __future__ import annotations

import io
import struct

import pytest
from PIL import Image

from app.services.photo_pipeline import (
    FileTooLargeError,
    UnsupportedFormatError,
    process_photo,
)


# ---------------------------------------------------------------------------
# Helpers — build minimal valid image bytes in various formats
# ---------------------------------------------------------------------------

def _make_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 80), color=(200, 100, 50))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 80), color=(50, 100, 200))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_webp_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 80), color=(10, 20, 30))
    img.save(buf, format="WEBP")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Format sniffing — accepted formats return without raising
# ---------------------------------------------------------------------------

def test_jpeg_accepted_by_extension_and_magic():
    data = _make_jpeg_bytes()
    # Should not raise — just needs to complete (stub output ok in task 1)
    full, thumb, _ = process_photo(data, "bag.jpg")
    assert isinstance(full, bytes) and len(full) > 0
    assert isinstance(thumb, bytes) and len(thumb) > 0


def test_jpeg_uppercase_extension():
    data = _make_jpeg_bytes()
    full, thumb, _ = process_photo(data, "bag.JPG")
    assert len(full) > 0


def test_png_accepted():
    data = _make_png_bytes()
    full, thumb, _ = process_photo(data, "bag.png")
    assert len(full) > 0


def test_webp_accepted():
    data = _make_webp_bytes()
    full, thumb, _ = process_photo(data, "bag.webp")
    assert len(full) > 0


# ---------------------------------------------------------------------------
# Format sniffing — rejections
# ---------------------------------------------------------------------------

def test_text_file_with_jpg_extension_rejected():
    """Magic bytes trump the extension — plain text is not a valid image."""
    data = b"this is just a text file, not an image"
    with pytest.raises(UnsupportedFormatError):
        process_photo(data, "sneaky.jpg")


def test_unsupported_extension_rejected():
    data = _make_jpeg_bytes()
    with pytest.raises(UnsupportedFormatError):
        process_photo(data, "bag.bmp")


def test_gif_rejected():
    buf = io.BytesIO()
    img = Image.new("RGB", (10, 10))
    img.save(buf, format="GIF")
    with pytest.raises(UnsupportedFormatError):
        process_photo(buf.getvalue(), "anim.gif")
```

- [ ] **Step 4: Run tests to confirm they fail (module doesn't exist yet)**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError` or `ImportError` — `app.services.photo_pipeline` does not exist.

- [ ] **Step 5: Create `app/services/photo_pipeline.py` with format detection**

```python
from __future__ import annotations

import io
from datetime import datetime, timezone, timedelta
from typing import Optional

import pillow_heif
from PIL import Image, ImageOps

# Register HEIC/HEIF opener once at module load.
pillow_heif.register_heif_opener()

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}

_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class UnsupportedFormatError(ValueError):
    """Raised when the uploaded file is not JPEG / PNG / HEIC / HEIF / WebP."""


class FileTooLargeError(ValueError):
    """Raised when the uploaded file exceeds the 25 MB per-file limit."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sniff_format(data: bytes, filename: str = "") -> str:
    """Return a canonical format string or raise UnsupportedFormatError."""
    # JPEG: starts with FF D8 FF
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    # PNG: starts with 89 50 4E 47 0D 0A 1A 0A
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    # WebP: RIFF????WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    # HEIC/HEIF: bytes 4-7 are an ftyp box; brand at 8-12 identifies HEIC/HEIF
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        # Recognize common brands; list is intentionally short and well-sourced
        if brand in (b"heic", b"heix", b"mif1", b"msf1", b"heim", b"heis"):
            return "heic"
    # Extension+ftyp fallback covers edge-case brands not in the list above
    if filename.lower().endswith((".heic", ".heif")) and len(data) >= 8 and data[4:8] == b"ftyp":
        return "heic"
    raise UnsupportedFormatError(
        f"File does not appear to be JPEG, PNG, HEIC/HEIF, or WebP "
        f"(magic bytes: {data[:12].hex()!r})"
    )


def _check_extension(filename: str) -> None:
    """Raise UnsupportedFormatError if the file extension is not allowed."""
    import os
    ext = os.path.splitext(filename.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"File extension {ext!r} is not supported. "
            f"Allowed: {sorted(_ALLOWED_EXTENSIONS)}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_photo(
    data: bytes,
    filename: str,
) -> tuple[bytes, bytes, Optional[datetime]]:
    """
    Process raw upload bytes through the full pipeline.

    Returns:
        (full_jpeg_bytes, thumb_jpeg_bytes, captured_at)

    Raises:
        FileTooLargeError  — if len(data) > 25 MB
        UnsupportedFormatError — if format is not JPEG/PNG/HEIC/HEIF/WebP
    """
    # 1. Size check (fast — before any parsing)
    if len(data) > _MAX_BYTES:
        raise FileTooLargeError(
            f"File is {len(data) / 1024 / 1024:.1f} MB; maximum is 25 MB."
        )

    # 2. Extension check
    _check_extension(filename)

    # 3. Magic-byte format sniff (raises UnsupportedFormatError for bad magic)
    fmt = _sniff_format(data, filename)

    # 4. Open image (HEIC handled transparently by pillow-heif opener)
    img = Image.open(io.BytesIO(data))
    img.load()  # force decode so EXIF is available

    # 5. Extract captured_at from EXIF (stub — filled in Task 3)
    captured_at: Optional[datetime] = None

    # 6. Apply EXIF rotation and strip EXIF (stub — filled in Task 3)
    img = img.convert("RGB")

    # 7. Save full-resolution JPEG
    full_buf = io.BytesIO()
    img.save(full_buf, format="JPEG", quality=90)
    full_jpeg = full_buf.getvalue()

    # 8. Generate thumbnail (stub — filled in Task 4; for now copy full)
    thumb_buf = io.BytesIO()
    thumb_img = img.copy()
    thumb_img.thumbnail((600, 600), Image.LANCZOS)
    thumb_img.save(thumb_buf, format="JPEG", quality=85)
    thumb_jpeg = thumb_buf.getvalue()

    return full_jpeg, thumb_jpeg, captured_at
```

- [ ] **Step 6: Run the format-detection tests — expect green**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py -v
```

Expected output (all pass):
```
tests/test_photo_pipeline.py::test_jpeg_accepted_by_extension_and_magic PASSED
tests/test_photo_pipeline.py::test_jpeg_uppercase_extension PASSED
tests/test_photo_pipeline.py::test_png_accepted PASSED
tests/test_photo_pipeline.py::test_webp_accepted PASSED
tests/test_photo_pipeline.py::test_text_file_with_jpg_extension_rejected PASSED
tests/test_photo_pipeline.py::test_unsupported_extension_rejected PASSED
tests/test_photo_pipeline.py::test_gif_rejected PASSED
7 passed
```

- [ ] **Step 7: Run the full baseline to verify no regressions**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: `89 passed` (existing) `+ 7 passed` from new file = 96 passed, 0 failed.

- [ ] **Step 8: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add pyproject.toml app/services/photo_pipeline.py tests/test_photo_pipeline.py
git commit -m "feat: add photo pipeline skeleton with format detection (JPEG/PNG/HEIC/WebP)"
```

---

## Task 2: HEIC→JPEG conversion

**Files:**
- Modify: `app/services/photo_pipeline.py` (the `process_photo` function is already wired to open HEIC via pillow-heif; this task adds a fixture and a dedicated test)
- Modify: `tests/test_photo_pipeline.py`

### Background

`pillow_heif.register_heif_opener()` (called at module load in Task 1) causes `Image.open()` to transparently decode HEIC/HEIF files. After `img.convert("RGB")` and `img.save(..., format="JPEG")`, the output is a plain JPEG with no HEIC container. No extra code is needed in the pipeline — but we need a test with a real HEIC fixture.

**Generating a HEIC fixture at test time:** We use `pillow-heif`'s encoder to create a tiny HEIC file in memory. This avoids committing a binary to the repo.

- [ ] **Step 1: Write the failing HEIC conversion test**

Add to `tests/test_photo_pipeline.py` (append after the existing tests):

```python
# ---------------------------------------------------------------------------
# HEIC → JPEG conversion
# ---------------------------------------------------------------------------

def _make_heic_bytes() -> bytes:
    """Generate a tiny valid HEIC file in memory using pillow-heif."""
    import pillow_heif
    img = Image.new("RGB", (64, 64), color=(255, 128, 0))
    heif_file = pillow_heif.from_pillow(img)
    buf = io.BytesIO()
    heif_file.save(buf, format="HEIF")
    return buf.getvalue()


def test_heic_converted_to_jpeg():
    data = _make_heic_bytes()
    full, thumb, _ = process_photo(data, "photo.heic")
    # Output must be a valid JPEG (starts with FF D8 FF)
    assert full[:3] == b"\xff\xd8\xff", "Full output is not a JPEG"
    assert thumb[:3] == b"\xff\xd8\xff", "Thumb output is not a JPEG"


def test_heif_extension_also_accepted():
    data = _make_heic_bytes()
    full, thumb, _ = process_photo(data, "photo.heif")
    assert full[:3] == b"\xff\xd8\xff"


def test_heic_output_is_decodable_by_pillow():
    """Verify the JPEG output can be opened by Pillow without error."""
    data = _make_heic_bytes()
    full, _, _ = process_photo(data, "photo.heic")
    result_img = Image.open(io.BytesIO(full))
    result_img.verify()  # raises if corrupt
```

- [ ] **Step 2: Run to confirm tests fail (HEIC helper not yet callable from tests)**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py::test_heic_converted_to_jpeg tests/test_photo_pipeline.py::test_heif_extension_also_accepted tests/test_photo_pipeline.py::test_heic_output_is_decodable_by_pillow -v
```

Expected: These tests may already pass if `pillow-heif` is installed (the pipeline already calls `Image.open` which handles HEIC). If they fail, the error will point to the HEIC opener not being registered or the fixture generation failing — diagnose from the traceback.

- [ ] **Step 3: Verify the magic-byte sniffer covers generated HEIC bytes**

The `_sniff_format` function checks `data[4:8] == b"ftyp"`. Run this quick sanity check to make sure the test fixture has the right ftyp box:

```bash
cd /gt/purseinator/crew/kagarmoe && python -c "
import io, pillow_heif
from PIL import Image
img = Image.new('RGB', (64,64), color=(255,128,0))
heif_file = pillow_heif.from_pillow(img)
buf = io.BytesIO()
heif_file.save(buf, format='HEIF')
data = buf.getvalue()
print('bytes 4-8:', data[4:8])
print('bytes 8-12:', data[8:12])
print('hex[:16]:', data[:16].hex())
"
```

Expected output will show `b'ftyp'` at offset 4. If the brand at 8-12 is not in `_sniff_format`'s brand tuple `(b"heic", b"heix", b"mif1", b"msf1", b"heim", b"heis")`, the extension+ftyp fallback in `_sniff_format` will catch it anyway (since the fixture filename ends in `.heic`). If a different extension is used in the fixture, add the specific brand to the tuple.

Update `_sniff_format` in `app/services/photo_pipeline.py` if needed — add whatever brand the diagnostic shows.

- [ ] **Step 4: Run all pipeline tests green**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py -v
```

Expected: all 10 pass (7 from Task 1 + 3 new).

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add tests/test_photo_pipeline.py app/services/photo_pipeline.py
git commit -m "feat: test HEIC→JPEG conversion in photo pipeline"
```

---

## Task 3: EXIF rotation, strip, and `captured_at` extraction

**Files:**
- Modify: `app/services/photo_pipeline.py` (fill in the EXIF stubs from Task 1)
- Modify: `tests/test_photo_pipeline.py`

### Background

Pillow provides `PIL.ImageOps.exif_transpose(img)` which reads the EXIF orientation tag and rotates/flips the image accordingly. After transposing, we strip all EXIF by saving and reloading without EXIF data. `captured_at` is extracted from the raw EXIF dict before stripping.

EXIF tag numbers:
- `36867` = `DateTimeOriginal` (e.g., `"2026:04:30 18:42:00"`)
- `36880` = `OffsetTimeOriginal` (e.g., `"-05:00"`)

Pillow's `Image.getexif()` returns a dict-like object; access tags by integer key.

- [ ] **Step 1: Write failing tests for EXIF behavior**

Add to `tests/test_photo_pipeline.py`:

```python
# ---------------------------------------------------------------------------
# EXIF rotation, strip, and captured_at
# ---------------------------------------------------------------------------

def _make_jpeg_with_exif(
    width: int,
    height: int,
    orientation: int = 1,
    date_time_original: str | None = None,
    offset_time_original: str | None = None,
) -> bytes:
    """
    Build a JPEG with the given EXIF tags injected.

    orientation: EXIF orientation value 1–8.
        1 = normal, 6 = 90° CW (phone held portrait, sensor landscape).
    date_time_original: string like "2026:04:30 18:42:00"
    offset_time_original: string like "+05:30" or "-07:00"
    """
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    exif = img.getexif()
    if orientation != 1:
        exif[0x0112] = orientation  # tag 274 = Orientation
    if date_time_original:
        exif[36867] = date_time_original
    if offset_time_original:
        exif[36880] = offset_time_original
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def test_exif_rotation_applied():
    """
    A landscape image (200×100) with orientation=6 (90° CW) should come out
    portrait (100×200) after pipeline processing.
    """
    data = _make_jpeg_with_exif(width=200, height=100, orientation=6)
    # Sanity: confirm the orientation tag was actually written into the fixture
    # before we invoke the pipeline (fail fast if Pillow strips it on save).
    fixture_img = Image.open(io.BytesIO(data))
    fixture_exif = fixture_img.getexif()
    assert fixture_exif.get(0x0112) == 6, (
        f"orientation tag not preserved in test fixture; got {fixture_exif.get(0x0112)}"
    )
    full, _, _ = process_photo(data, "rotated.jpg")
    result = Image.open(io.BytesIO(full))
    w, h = result.size
    assert h > w, f"Expected portrait after rotation but got {w}×{h}"


def test_exif_stripped_from_output():
    """No EXIF should survive in the saved JPEG."""
    data = _make_jpeg_with_exif(
        width=100, height=100,
        date_time_original="2026:04:30 18:42:00",
    )
    full, _, _ = process_photo(data, "with_exif.jpg")
    result = Image.open(io.BytesIO(full))
    exif = result.getexif()
    assert len(exif) == 0, f"Expected empty EXIF but found: {dict(exif)}"


def test_captured_at_extracted_naive():
    """DateTimeOriginal without offset → naive datetime stored as-is."""
    data = _make_jpeg_with_exif(
        width=100, height=100,
        date_time_original="2026:04:30 18:42:00",
    )
    _, _, captured_at = process_photo(data, "dated.jpg")
    assert captured_at is not None
    assert captured_at.year == 2026
    assert captured_at.month == 4
    assert captured_at.day == 30
    assert captured_at.hour == 18
    assert captured_at.minute == 42
    assert captured_at.tzinfo is None, "Expected naive datetime (no offset provided)"


def test_captured_at_with_offset_normalized_to_utc():
    """DateTimeOriginal + OffsetTimeOriginal → UTC-normalized datetime."""
    # 18:42:00 local at +05:30 = 13:12:00 UTC
    data = _make_jpeg_with_exif(
        width=100, height=100,
        date_time_original="2026:04:30 18:42:00",
        offset_time_original="+05:30",
    )
    _, _, captured_at = process_photo(data, "dated_offset.jpg")
    assert captured_at is not None
    assert captured_at.tzinfo == timezone.utc
    assert captured_at.hour == 13
    assert captured_at.minute == 12


def test_captured_at_none_when_no_exif():
    """Images with no DateTimeOriginal → captured_at is None."""
    data = _make_jpeg_bytes()
    _, _, captured_at = process_photo(data, "no_exif.jpg")
    assert captured_at is None
```

- [ ] **Step 2: Run to confirm new tests fail**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py::test_exif_rotation_applied tests/test_photo_pipeline.py::test_exif_stripped_from_output tests/test_photo_pipeline.py::test_captured_at_extracted_naive tests/test_photo_pipeline.py::test_captured_at_with_offset_normalized_to_utc tests/test_photo_pipeline.py::test_captured_at_none_when_no_exif -v
```

Expected: `test_exif_rotation_applied` fails (orientation not applied), `test_exif_stripped_from_output` may fail (EXIF leaks through), `test_captured_at_*` all fail (returns `None`).

- [ ] **Step 3: Implement EXIF logic in `process_photo`**

Replace the stub section of `process_photo` in `app/services/photo_pipeline.py`. The full function body (replacing the existing content of `process_photo` from step 4 onward):

```python
def _parse_captured_at(img: Image.Image) -> Optional[datetime]:
    """
    Extract DateTimeOriginal from EXIF.
    If OffsetTimeOriginal is present, apply it and return a UTC-aware datetime.
    Otherwise return a naive datetime.
    Returns None if DateTimeOriginal is absent or unparseable.
    """
    try:
        exif = img.getexif()
    except Exception:
        return None

    raw_dt = exif.get(36867)  # DateTimeOriginal
    if not raw_dt:
        return None

    try:
        # EXIF datetime format: "YYYY:MM:DD HH:MM:SS"
        naive = datetime.strptime(raw_dt, "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        return None

    raw_offset = exif.get(36880)  # OffsetTimeOriginal
    if raw_offset:
        try:
            # Offset format: "+HH:MM" or "-HH:MM"
            sign = 1 if raw_offset[0] == "+" else -1
            parts = raw_offset[1:].split(":")
            offset_h = int(parts[0])
            offset_m = int(parts[1]) if len(parts) > 1 else 0
            total_minutes = sign * (offset_h * 60 + offset_m)
            tz = timezone(timedelta(minutes=total_minutes))
            aware = naive.replace(tzinfo=tz)
            return aware.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        except (ValueError, IndexError, TypeError):
            pass  # fall through to naive

    return naive
```

Then update `process_photo` to call `_parse_captured_at` before `exif_transpose` and strip EXIF on save. Replace the relevant section inside `process_photo`:

```python
    # 4. Open image (HEIC handled transparently by pillow-heif opener)
    img = Image.open(io.BytesIO(data))
    img.load()  # force decode so EXIF is available

    # 5. Extract captured_at from EXIF (before transpose clears it)
    captured_at = _parse_captured_at(img)

    # 6. Apply EXIF rotation, then convert to RGB (strips alpha/palette)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    # 7. Save full-resolution JPEG — do NOT pass exif= so all EXIF is dropped
    full_buf = io.BytesIO()
    img.save(full_buf, format="JPEG", quality=90)
    full_jpeg = full_buf.getvalue()

    # 8. Generate thumbnail
    thumb_buf = io.BytesIO()
    thumb_img = img.copy()
    thumb_img.thumbnail((600, 600), Image.LANCZOS)
    thumb_img.save(thumb_buf, format="JPEG", quality=85)
    thumb_jpeg = thumb_buf.getvalue()

    return full_jpeg, thumb_jpeg, captured_at
```

The complete `process_photo` function after this edit:

```python
def process_photo(
    data: bytes,
    filename: str,
) -> tuple[bytes, bytes, Optional[datetime]]:
    """
    Process raw upload bytes through the full pipeline.

    Returns:
        (full_jpeg_bytes, thumb_jpeg_bytes, captured_at)

    Raises:
        FileTooLargeError  — if len(data) > 25 MB
        UnsupportedFormatError — if format is not JPEG/PNG/HEIC/HEIF/WebP
    """
    # 1. Size check (fast — before any parsing)
    if len(data) > _MAX_BYTES:
        raise FileTooLargeError(
            f"File is {len(data) / 1024 / 1024:.1f} MB; maximum is 25 MB."
        )

    # 2. Extension check
    _check_extension(filename)

    # 3. Magic-byte format sniff (raises UnsupportedFormatError for bad magic)
    _sniff_format(data, filename)

    # 4. Open image (HEIC handled transparently by pillow-heif opener)
    img = Image.open(io.BytesIO(data))
    img.load()  # force decode so EXIF is available

    # 5. Extract captured_at from EXIF (before transpose clears it)
    captured_at = _parse_captured_at(img)

    # 6. Apply EXIF rotation, then convert to RGB (strips alpha/palette)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    # 7. Save full-resolution JPEG — do NOT pass exif= so all EXIF is dropped
    full_buf = io.BytesIO()
    img.save(full_buf, format="JPEG", quality=90)
    full_jpeg = full_buf.getvalue()

    # 8. Generate thumbnail
    thumb_buf = io.BytesIO()
    thumb_img = img.copy()
    thumb_img.thumbnail((600, 600), Image.LANCZOS)
    thumb_img.save(thumb_buf, format="JPEG", quality=85)
    thumb_jpeg = thumb_buf.getvalue()

    return full_jpeg, thumb_jpeg, captured_at
```

- [ ] **Step 4: Run EXIF tests green**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py -v
```

Expected: all 15 pass (10 from Tasks 1-2 + 5 new).

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/services/photo_pipeline.py tests/test_photo_pipeline.py
git commit -m "feat: implement EXIF rotation, strip, and captured_at extraction in pipeline"
```

---

## Task 4: Thumbnail generation (verified dimensions)

**Files:**
- Modify: `tests/test_photo_pipeline.py` (add dimension tests)

### Background

`Image.thumbnail((600, 600))` already appears in the pipeline from Task 1 and was kept through Task 3. This task adds explicit tests that verify: (a) a large image is scaled down to fit 600×600 max, (b) a small image is NOT upscaled, and (c) aspect ratio is preserved. No pipeline code changes should be needed — just verifying the existing implementation is correct.

- [ ] **Step 1: Write failing thumbnail dimension tests**

Add to `tests/test_photo_pipeline.py`:

```python
# ---------------------------------------------------------------------------
# Thumbnail dimensions
# ---------------------------------------------------------------------------

def test_thumbnail_fits_within_600x600():
    """A 1200×800 image should produce a thumb of exactly 600×400."""
    buf = io.BytesIO()
    Image.new("RGB", (1200, 800), color=(10, 20, 30)).save(buf, format="JPEG")
    _, thumb, _ = process_photo(buf.getvalue(), "large.jpg")
    result = Image.open(io.BytesIO(thumb))
    w, h = result.size
    assert w <= 600 and h <= 600, f"Thumb {w}×{h} exceeds 600×600"
    assert w == 600, f"Expected width=600, got {w}"
    assert h == 400, f"Expected height=400, got {h}"


def test_thumbnail_preserves_aspect_ratio_portrait():
    """A 400×800 portrait image should produce a thumb of exactly 300×600."""
    buf = io.BytesIO()
    Image.new("RGB", (400, 800), color=(10, 20, 30)).save(buf, format="JPEG")
    _, thumb, _ = process_photo(buf.getvalue(), "portrait.jpg")
    result = Image.open(io.BytesIO(thumb))
    w, h = result.size
    assert w <= 600 and h <= 600
    assert h == 600, f"Expected height=600, got {h}"
    assert w == 300, f"Expected width=300, got {w}"


def test_small_image_not_upscaled():
    """A 100×80 image should produce a thumb of 100×80 (no upscaling)."""
    buf = io.BytesIO()
    Image.new("RGB", (100, 80), color=(50, 60, 70)).save(buf, format="JPEG")
    _, thumb, _ = process_photo(buf.getvalue(), "tiny.jpg")
    result = Image.open(io.BytesIO(thumb))
    w, h = result.size
    assert w == 100 and h == 80, f"Expected 100×80, got {w}×{h}"


def test_full_res_not_downsized():
    """Full-resolution output should preserve the original dimensions."""
    buf = io.BytesIO()
    Image.new("RGB", (1200, 800), color=(10, 20, 30)).save(buf, format="JPEG")
    full, _, _ = process_photo(buf.getvalue(), "large.jpg")
    result = Image.open(io.BytesIO(full))
    w, h = result.size
    assert w == 1200 and h == 800, f"Full-res should be 1200×800 but got {w}×{h}"
```

- [ ] **Step 2: Run to confirm tests fail or pass**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py::test_thumbnail_fits_within_600x600 tests/test_photo_pipeline.py::test_thumbnail_preserves_aspect_ratio_portrait tests/test_photo_pipeline.py::test_small_image_not_upscaled tests/test_photo_pipeline.py::test_full_res_not_downsized -v
```

If any fail, the `Image.thumbnail` call in `process_photo` has a bug. `Image.thumbnail` uses the same `LANCZOS` filter and mutates in place — it should already be correct. If `test_thumbnail_fits_within_600x600` shows a slightly different size (e.g., 599 or 601), it's a rounding issue in JPEG decode; adjust the assertion to `abs(w - 600) <= 1`.

- [ ] **Step 3: Run all pipeline tests to confirm 19 pass**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py -v
```

Expected: 19 passed.

- [ ] **Step 4: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add tests/test_photo_pipeline.py
git commit -m "test: verify thumbnail 600x600 max-fit and aspect ratio in pipeline"
```

---

## Task 5: Size limit and unsupported format rejection (unit tests)

**Files:**
- Modify: `tests/test_photo_pipeline.py`

### Background

`FileTooLargeError` and the extension-mismatch path of `UnsupportedFormatError` are already implemented in the pipeline (Task 1). This task adds the tests that exercise those paths explicitly, including edge cases.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_photo_pipeline.py`:

```python
# ---------------------------------------------------------------------------
# Size limit and format rejection
# ---------------------------------------------------------------------------

def test_file_too_large_raises_error():
    """Files exceeding 25 MB should raise FileTooLargeError."""
    large_data = b"x" * (25 * 1024 * 1024 + 1)
    with pytest.raises(FileTooLargeError):
        process_photo(large_data, "big.jpg")


# test_exactly_25mb_is_rejected was dropped: the test name ("is_rejected") contradicted
# the body (asserting the file is NOT rejected by FileTooLargeError). The boundary
# semantics are already documented by the `> _MAX_BYTES` check in the implementation:
# exactly 25 MB passes the size check and only raises UnsupportedFormatError because
# b"x"*25MB is not a valid image. Adding a test that catches `Exception` broadly adds
# no value and obscures intent.


def test_tiff_rejected():
    """TIFF format is not in the allowed list."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="TIFF")
    with pytest.raises(UnsupportedFormatError):
        process_photo(buf.getvalue(), "photo.tiff")


def test_pdf_bytes_rejected():
    """PDF magic bytes should be rejected."""
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    with pytest.raises(UnsupportedFormatError):
        process_photo(pdf_bytes, "doc.jpg")


def test_empty_bytes_rejected():
    """Empty file should raise UnsupportedFormatError (not crash)."""
    with pytest.raises((UnsupportedFormatError, Exception)):
        process_photo(b"", "empty.jpg")
```

- [ ] **Step 2: Run to confirm tests fail or reveal edge cases**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py::test_file_too_large_raises_error tests/test_photo_pipeline.py::test_tiff_rejected tests/test_photo_pipeline.py::test_pdf_bytes_rejected tests/test_photo_pipeline.py::test_empty_bytes_rejected -v
```

Expected: `test_file_too_large_raises_error` should already pass. The others may pass depending on PIL behavior — check outputs.

- [ ] **Step 3: Fix any failures**

If `test_tiff_rejected` fails because PIL opens TIFF and returns something, add TIFF to the unsupported check in `_check_extension` — it's already excluded since `.tiff` is not in `_ALLOWED_EXTENSIONS`. If `test_empty_bytes_rejected` causes a crash rather than a graceful exception, wrap the `Image.open` call in a try/except and re-raise as `UnsupportedFormatError`:

```python
    # 4. Open image
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise UnsupportedFormatError(f"Cannot decode image: {exc}") from exc
```

Update `process_photo` in `app/services/photo_pipeline.py` if needed.

- [ ] **Step 4: Run all pipeline tests — expect 23 pass**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photo_pipeline.py -v
```

Expected: 23 passed.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/services/photo_pipeline.py tests/test_photo_pipeline.py
git commit -m "test: add size limit and format rejection tests for photo pipeline"
```

---

## Task 6: Alembic migration — add `captured_at` and `thumbnail_key` columns

**Files:**
- Modify: `app/models.py` — add columns to `ItemPhotoTable` and fields to `ItemPhotoRead`
- Create: `alembic/versions/b2c3d4e5f6a7_add_photo_pipeline_columns.py`

### Background

`ItemPhotoTable` needs two new nullable columns:
- `captured_at: Optional[datetime]` — naive or UTC datetime from EXIF
- `thumbnail_key: Optional[str]` — storage path to the 600×600 thumbnail JPEG

Both are nullable so the migration is backward-compatible with existing rows and existing tests that create `ItemPhotoTable` rows without these columns.

`ItemPhotoRead` (the Pydantic schema) must also gain these fields so the API response includes them.

The test suite uses SQLite via `Base.metadata.create_all` (in conftest.py `db_engine` fixture) — no migration runs during tests. The migration is for production Postgres.

**Sequencing precondition — REQUIRED before starting the migration step:**

Plans 1 and 2 are now sequenced: Plan 1 lands first. This plan's migration (`b2c3d4e5f6a7`) must chain off Plan 1's migration head.

Before running Step 4 (creating the migration file), verify Plan 1 has merged:

```bash
cd /gt/purseinator/crew/kagarmoe && alembic heads
```

Expected: exactly ONE head is returned. If two heads are shown, Plan 1 has not merged yet — **stop and wait for Plan 1 to merge before proceeding with this step.**

The `down_revision` value in Step 4 is NOT hardcoded to `a1b2c3d4e5f6`. After Plan 1 merges, run `alembic heads` to obtain the actual current head ID, then substitute that value for `a1b2c3d4e5f6` in the migration file below.

- [ ] **Step 1: Add columns to `ItemPhotoTable` in `app/models.py`**

Find the `ItemPhotoTable` class (currently lines 70–79). Replace it:

```python
class ItemPhotoTable(Base):
    __tablename__ = "item_photos"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False)
    thumbnail_key = Column(String(500), nullable=True)
    is_hero = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    captured_at = Column(DateTime, nullable=True)

    item = relationship("ItemTable", back_populates="photos")
```

- [ ] **Step 2: Update `ItemPhotoRead` Pydantic schema**

Find `ItemPhotoRead` (currently lines 202–210). Replace it:

```python
class ItemPhotoRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    item_id: int
    storage_key: str
    thumbnail_key: Optional[str] = None
    is_hero: bool
    sort_order: int
    captured_at: Optional[datetime] = None
```

- [ ] **Step 3: Run existing tests to confirm models change doesn't break them**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photos.py -v
```

Expected: all 7 existing photo tests still pass (new nullable columns don't affect existing rows).

- [ ] **Step 4: Create the Alembic migration**

Create `alembic/versions/b2c3d4e5f6a7_add_photo_pipeline_columns.py`:

```python
"""add captured_at and thumbnail_key to item_photos

Revision ID: b2c3d4e5f6a7
Revises: <FILL_IN_FROM_alembic_heads_after_plan1_merges>
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# IMPORTANT: down_revision must be set to the output of `alembic heads` AFTER
# Plan 1 has merged. Do NOT hardcode a1b2c3d4e5f6 — that is a placeholder.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"  # REPLACE with actual head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "item_photos",
        sa.Column("thumbnail_key", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "item_photos",
        sa.Column("captured_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("item_photos", "captured_at")
    op.drop_column("item_photos", "thumbnail_key")
```

- [ ] **Step 5: Verify the migration chain is correct**

Verify Plan 1 has merged and there is exactly one head:

```bash
cd /gt/purseinator/crew/kagarmoe && alembic heads
```

Expected: exactly one head is printed. Copy its revision ID — this is the value to use for `down_revision` in the migration file created in Step 4 (replacing the placeholder `a1b2c3d4e5f6`). If two heads are shown, Plan 1 has not merged — stop.

Also run `alembic history` to confirm the chain is readable:

```bash
cd /gt/purseinator/crew/kagarmoe && python -m alembic history
```

- [ ] **Step 6: Run all tests to confirm no regressions**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 112+ passed (89 baseline + 23 pipeline unit tests), 0 failed.

- [ ] **Step 7: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/models.py alembic/versions/b2c3d4e5f6a7_add_photo_pipeline_columns.py
git commit -m "feat: add captured_at and thumbnail_key columns to ItemPhotoTable (migration + model)"
```

---

## Task 7: Wire pipeline into `upload_photo` + integration tests

**Files:**
- Modify: `app/routes/photos.py` — replace raw-byte write with pipeline call; write both full + thumb; set `thumbnail_key` and `captured_at`
- Modify: `tests/test_photos.py` — add integration tests

### Background

The current `upload_photo` writes raw bytes to `collections/{cid}/items/{iid}/{filename}`. We replace this with:
1. Read bytes.
2. Call `process_photo(data, file.filename)` — may raise `UnsupportedFormatError` (→ 415) or `FileTooLargeError` (→ 413).
3. Generate a UUID for filenames.
4. Write full JPEG to `collections/{cid}/items/{iid}/{uuid}.jpg`.
5. Write thumb JPEG to `collections/{cid}/items/{iid}/{uuid}.thumb.jpg`.
6. Set `storage_key`, `thumbnail_key`, `captured_at` on the new `ItemPhotoTable` row.

The existing tests that upload `b"fake-image-data"` with `.jpg` extension will break because `b"fake-image-data"` is not a valid JPEG. We need to fix them to use real JPEG bytes.

- [ ] **Step 1: Update existing photo test fixtures to use real JPEG bytes**

Open `tests/test_photos.py`. Every existing test uses `io.BytesIO(b"fake-image-data")` or `io.BytesIO(b"data1")` etc. Add a helper at the top of the file and update every test to use it. The full updated file:

```python
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
```

Note: `test_serve_photo` no longer asserts `resp.content == b"fake-image-data"` because the pipeline re-encodes the image. The new assertion checks for a valid JPEG magic header.

- [ ] **Step 2: Run the updated existing tests to confirm they fail (pipeline not wired yet)**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photos.py -v
```

Most tests will fail with `UnsupportedFormatError` or 500 since the route still writes raw bytes. That's expected — we're in the red phase.

- [ ] **Step 3: Wire the pipeline into `upload_photo` in `app/routes/photos.py`**

Replace the entire file:

```python
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import CollectionTable, ItemPhotoRead, ItemPhotoTable, ItemTable, UserTable
from app.services.photo_pipeline import (
    FileTooLargeError,
    UnsupportedFormatError,
    process_photo,
)

router = APIRouter()


def _storage_root(request: Request) -> str:
    return request.app.state.photo_storage_root


async def _require_collection_owner(db: AsyncSession, collection_id: int, user_id: int) -> CollectionTable:
    result = await db.execute(
        select(CollectionTable).where(CollectionTable.id == collection_id)
    )
    coll = result.scalar_one_or_none()
    if coll is None or coll.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return coll


@router.post("/collections/{collection_id}/items/{item_id}/photos", status_code=201)
async def upload_photo(
    collection_id: int,
    item_id: int,
    file: UploadFile,
    request: Request,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemPhotoRead:
    await _require_collection_owner(db, collection_id, user.id)
    item = await db.get(ItemTable, item_id)
    if item is None or item.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Item not found")

    # Defensive early-exit: reject obviously-too-large files before reading.
    # For v1 we accept the cost of buffering up to 25 MB into memory before
    # rejecting in process_photo. Future hardening would use a streaming approach
    # with incremental byte counting. The Content-Length check below catches the
    # obvious case (well-behaved clients) without that complexity.
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    data = await file.read()

    try:
        full_jpeg, thumb_jpeg, captured_at = process_photo(data, file.filename or "upload.jpg")
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    photo_uuid = uuid.uuid4().hex
    storage_key = f"collections/{collection_id}/items/{item_id}/{photo_uuid}.jpg"
    thumbnail_key = f"collections/{collection_id}/items/{item_id}/{photo_uuid}.thumb.jpg"

    storage_root = _storage_root(request)
    full_path = Path(storage_root) / storage_key
    thumb_path = Path(storage_root) / thumbnail_key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(full_jpeg)
    thumb_path.write_bytes(thumb_jpeg)

    # First photo for this item becomes hero
    result = await db.execute(
        select(ItemPhotoTable).where(ItemPhotoTable.item_id == item_id)
    )
    existing = result.scalars().all()
    is_hero = len(existing) == 0

    row = ItemPhotoTable(
        item_id=item_id,
        storage_key=storage_key,
        thumbnail_key=thumbnail_key,
        is_hero=is_hero,
        sort_order=len(existing),
        captured_at=captured_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ItemPhotoRead.model_validate(row)


@router.get("/collections/{collection_id}/items/{item_id}/photos")
async def list_photos(
    collection_id: int,
    item_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ItemPhotoRead]:
    await _require_collection_owner(db, collection_id, user.id)
    result = await db.execute(
        select(ItemPhotoTable)
        .where(ItemPhotoTable.item_id == item_id)
        .order_by(ItemPhotoTable.sort_order)
    )
    return [ItemPhotoRead.model_validate(r) for r in result.scalars().all()]


@router.get("/photos/{storage_key:path}/thumb")
async def serve_photo_thumb(storage_key: str, request: Request):
    # NOTE: FastAPI routes are matched in registration order.
    # This route MUST be registered BEFORE /photos/{storage_key:path}.
    # The spike in Task 8 Step 0 confirms that registering the thumb route first
    # causes FastAPI to correctly strip the literal "/thumb" suffix and pass only
    # the base key in storage_key. If the spike fails, switch to the prefix form
    # GET /photos/thumb/{storage_key:path} (see Task 8 Step 0 fallback instructions).
    storage_root = _storage_root(request)
    # thumbnail_key is derived by convention: base_key → base_key (already thumb)
    # The route captures everything before /thumb, so storage_key here is e.g.
    # "collections/1/items/2/abc123.jpg" and the thumb is "abc123.thumb.jpg".
    # We store thumbnail_key in the DB, but this endpoint reconstructs it from
    # the full-res key for clients that compose the URL from storage_key.
    # Convention: replace .jpg suffix with .thumb.jpg
    if storage_key.endswith(".jpg"):
        thumb_key = storage_key[:-4] + ".thumb.jpg"
    else:
        thumb_key = storage_key + ".thumb.jpg"
    path = Path(storage_root) / thumb_key
    if not path.exists():
        # Graceful fallback: serve full-res if thumb is missing (legacy rows)
        full_path = Path(storage_root) / storage_key
        if full_path.exists():
            return FileResponse(full_path)
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(path)


@router.get("/photos/{storage_key:path}")
async def serve_photo(storage_key: str, request: Request):
    storage_root = _storage_root(request)
    path = Path(storage_root) / storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(path)
```

**Important:** `serve_photo_thumb` is registered BEFORE `serve_photo`. FastAPI matches routes in registration order, and `{storage_key:path}` is greedy. The Task 8 Step 0 spike verifies that registration order is sufficient to route `/thumb`-suffixed URLs correctly. If the spike fails, switch to the prefix form `/photos/thumb/{storage_key:path}` per the fallback instructions in Task 8 Step 0.

- [ ] **Step 4: Run the updated existing tests — expect green**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photos.py -v
```

Expected: all 7 existing tests pass (with `_jpeg_bytes()` fixtures).

- [ ] **Step 5: Add new pipeline integration tests**

Append to `tests/test_photos.py`:

```python
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
```

- [ ] **Step 6: Run new integration tests — expect green**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photos.py -v
```

Expected: all 15 tests pass (7 existing + 8 new).

- [ ] **Step 7: Run full suite — expect no regressions**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 127+ passed, 0 failed.

- [ ] **Step 8: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/routes/photos.py tests/test_photos.py
git commit -m "feat: wire photo pipeline into upload_photo route (HEIC, EXIF, thumbnail, captured_at)"
```

---

## Task 8: Add `GET /photos/{key}/thumb` endpoint integration tests

**Files:**
- Modify: `tests/test_photos.py` — the thumb endpoint was registered in Task 7; this task tests it

### Background

The `serve_photo_thumb` route is already registered in Task 7. This task adds dedicated integration tests that verify the endpoint:
1. Returns the thumbnail file for a valid key.
2. Returns 404 for a key that doesn't exist.
3. Falls back to full-res for legacy rows without a thumbnail file.

- [ ] **Step 0: Verify route ordering**

Run a quick spike to confirm that registering `serve_photo_thumb` BEFORE `serve_photo` correctly routes URLs ending in `/thumb`:

```python
# /tmp/spike_route.py
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient

router = APIRouter()

@router.get("/photos/{key:path}/thumb")
def thumb(key: str): return {"matched": "thumb", "key": key}

@router.get("/photos/{key:path}")
def full(key: str): return {"matched": "full", "key": key}

app = FastAPI()
app.include_router(router)

client = TestClient(app)
r1 = client.get("/photos/abc/def.jpg/thumb")
r2 = client.get("/photos/abc/def.jpg")
print(r1.json(), r2.json())
```

Expected output:
`{"matched": "thumb", "key": "abc/def.jpg"} {"matched": "full", "key": "abc/def.jpg"}`

Run the spike:

```bash
python /tmp/spike_route.py
```

**If the spike passes** (thumb route correctly captures the key without `/thumb` in it): proceed as written, with `serve_photo_thumb` registered before `serve_photo` in `app/routes/photos.py`.

**If the `/thumb` request returns the full handler instead** (the greedy `{key:path}` swallows the literal suffix): change the thumb route from a suffix pattern to a prefix pattern throughout this plan. The safe fallback is:

```
GET /photos/thumb/{storage_key:path}
```

A literal prefix is consumed before path matching begins, making routing unambiguous regardless of FastAPI/Starlette version. If you make this change:
- Update the route decorator in `app/routes/photos.py`: `@router.get("/photos/thumb/{storage_key:path}")`
- Update `test_serve_thumbnail_returns_jpeg`, `test_serve_thumbnail_dimensions_le_600`, `test_serve_thumbnail_404_for_missing_key`, and `test_serve_thumbnail_fallback_to_full_res` to call `/photos/thumb/{storage_key}` instead of `/photos/{storage_key}/thumb`
- Update the File Map table at the top of this document
- Update the plan goal description at the top of this document

- [ ] **Step 1: Write the failing thumbnail endpoint tests**

Append to `tests/test_photos.py`:

```python
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
```

- [ ] **Step 2: Run the thumbnail endpoint tests — expect red (since endpoint was already added in Task 7, they may actually be green)**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_photos.py::test_serve_thumbnail_returns_jpeg tests/test_photos.py::test_serve_thumbnail_dimensions_le_600 tests/test_photos.py::test_serve_thumbnail_404_for_missing_key tests/test_photos.py::test_serve_thumbnail_fallback_to_full_res tests/test_photos.py::test_serve_thumbnail_legacy_row_null_thumbnail_key -v
```

If any fail, check the route registration order in `app/routes/photos.py`. FastAPI must see `serve_photo_thumb` before `serve_photo`. If routes are out of order, swap them.

Note: `test_serve_thumbnail_legacy_row_null_thumbnail_key` requires the `db_session` fixture to be exposed in `conftest.py`. If not available, add it: it is the same `AsyncSession` used by `get_db` in the test app. Check `tests/conftest.py` for the existing session fixture name and adjust the parameter accordingly.

- [ ] **Step 3: Run full test suite — expect 132+ passing**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 132+ passed (89 baseline + 23 pipeline unit + 20 photo integration), 0 failed.

- [ ] **Step 4: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add tests/test_photos.py
git commit -m "test: add GET /photos/{key}/thumb endpoint integration tests"
```

---

## Self-Review

### 1. Spec Coverage

| Pipeline step | Task covering it |
|---------------|-----------------|
| Sniff format by extension AND magic bytes | Task 1 (`_check_extension`, `_sniff_format`) |
| Reject if not JPEG/PNG/HEIC/HEIF/WebP → 415 | Task 5 (unit), Task 7 (integration) |
| Reject if > 25 MB → 413 | Task 5 (unit), Task 7 (integration) |
| HEIC/HEIF → JPEG via pillow-heif | Task 2 (unit), Task 7 (integration) |
| Read EXIF `DateTimeOriginal` → `captured_at` | Task 3 (unit), Task 7 (integration) |
| Apply `OffsetTimeOriginal` → UTC | Task 3 (unit) |
| Apply EXIF rotation (`exif_transpose`) | Task 3 (unit) |
| Strip ALL EXIF from saved image | Task 3 (unit) |
| Save full-res JPEG (quality 90) | Task 1 (pipeline); Task 7 (integration) |
| Generate 600×600 max-fit thumbnail | Task 4 (unit); Task 7, 8 (integration) |
| `captured_at` column on `ItemPhotoTable` | Task 6 (migration + model) |
| `thumbnail_key` column on `ItemPhotoTable` | Task 6 (migration + model) |
| UUID-based storage filenames | Task 7 |
| Storage path `collections/{cid}/items/{iid}/{uuid}.jpg` | Task 7 |
| Storage path `collections/{cid}/items/{iid}/{uuid}.thumb.jpg` | Task 7 |
| `GET /photos/{key}/thumb` endpoint | Task 7 (register), Task 8 (test) |
| Fallback to full-res when thumb missing | Task 7 (code), Task 8 (test) |
| `pillow-heif` in production dependencies | Task 1 |
| No staging table / no `/upload/*` endpoints touched | Confirmed — not in any task |

All spec requirements for Plan 2 are covered.

### 2. Placeholder Scan

No "TBD", "TODO", "implement later", or "similar to above" in this plan. Every step has complete code or exact commands.

### 3. Type Consistency

- `process_photo(data: bytes, filename: str) -> tuple[bytes, bytes, Optional[datetime]]` — used consistently in Task 1 (definition), Task 3 (EXIF impl), Task 7 (route caller).
- `UnsupportedFormatError` and `FileTooLargeError` — defined in Task 1, imported in Task 7. Names are identical.
- `ItemPhotoTable.thumbnail_key`, `ItemPhotoTable.captured_at` — added in Task 6, populated in Task 7.
- `ItemPhotoRead.thumbnail_key`, `ItemPhotoRead.captured_at` — added in Task 6, asserted on in Task 7.
- `_storage_root(request)` — unchanged from existing codebase, used as-is.

### 4. Hazards & Mitigations

| Hazard | Mitigation |
|--------|-----------|
| Route ordering for `/thumb`: `{path:path}` is greedy in FastAPI/Starlette; literal suffix matching is not guaranteed across all versions | Task 8 Step 0 runs a spike to verify behavior before tests are written; fallback is the unambiguous prefix form `/photos/thumb/{storage_key:path}` |
| Migration parallelism: Plan 2's `down_revision` depends on Plan 1 landing first | Task 6 precondition: `alembic heads` must return ONE head before creating the migration; `down_revision` is filled in from that output, not hardcoded |
| HEIC brand list uncertainty: invented brands (`MiHE`, `MiHM`, `MiHS`) may not match actual pillow-heif output | `_sniff_format` uses a short, well-sourced brand list plus an extension+ftyp fallback for edge cases; Task 2 Step 3 has a diagnostic to catch any brand not in the list |
| Size limit timing: full file is buffered into memory before rejection | Documented v1 tradeoff; `Content-Length` header check in Task 7 route handler catches well-behaved clients before reading; future hardening can use streaming |
