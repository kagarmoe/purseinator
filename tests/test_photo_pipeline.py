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
