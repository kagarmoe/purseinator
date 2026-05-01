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
    from datetime import timezone
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
