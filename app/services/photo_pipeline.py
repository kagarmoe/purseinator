from __future__ import annotations

import io
import os
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
    ext = os.path.splitext(filename.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"File extension {ext!r} is not supported. "
            f"Allowed: {sorted(_ALLOWED_EXTENSIONS)}"
        )


def _parse_captured_at(img: Image.Image) -> Optional[datetime]:
    """
    Extract DateTimeOriginal from EXIF.
    If OffsetTimeOriginal is present, apply it and return a UTC-aware datetime.
    Otherwise return a naive datetime.
    Returns None if DateTimeOriginal is absent or unparseable.
    """
    try:
        exif = img.getexif()
    except (AttributeError, KeyError, ValueError, OSError):
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
            return aware.astimezone(timezone.utc)
        except (ValueError, IndexError, TypeError):
            pass  # fall through to naive

    return naive


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
    _sniff_format(data, filename)

    # 4. Open image (HEIC handled transparently by pillow-heif opener)
    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # force decode so EXIF is available
    except Exception as exc:
        raise UnsupportedFormatError(f"Cannot decode image: {exc}") from exc

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
