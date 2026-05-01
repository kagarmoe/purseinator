"""Upload + staging endpoints (B3–B8)."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, get_photo_storage_root
from app.models import (
    CollectionTable,
    ItemPhotoTable,
    ItemTable,
    StagingPhotoTable,
    UserTable,
)
from app.services.photo_pipeline import (
    FileTooLargeError,
    UnsupportedFormatError,
    process_photo,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_FILES = 50
_MAX_PER_FILE_BYTES = 25 * 1024 * 1024
_STAGING_CAP = 500


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class StagingPhotoOut(BaseModel):
    id: int
    thumbnail_url: str
    original_filename: Optional[str]
    captured_at: Optional[datetime]


class UploadFailure(BaseModel):
    original_filename: str
    reason: str


class UploadResponse(BaseModel):
    succeeded: list[StagingPhotoOut]
    failed: list[UploadFailure]


class StagingListResponse(BaseModel):
    photos: list[StagingPhotoOut]
    has_more: bool


class GroupRequest(BaseModel):
    collection_id: int
    photo_ids: list[int]


class GroupResponse(BaseModel):
    item_id: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _thumbnail_url(thumbnail_key: str) -> str:
    return f"/photos/{thumbnail_key}/thumb"


async def _require_collection_owner_404(db: AsyncSession, collection_id: int, user_id: int) -> CollectionTable:
    """Like _require_collection_owner but raises 404 instead of 403 to avoid existence oracle."""
    from app.routes.items import _require_collection_owner
    try:
        return await _require_collection_owner(db, collection_id, user_id)
    except HTTPException as e:
        if e.status_code == 403:
            raise HTTPException(status_code=404, detail="Collection not found")
        raise


# ---------------------------------------------------------------------------
# POST /upload/photos
# ---------------------------------------------------------------------------

@router.post("/photos", response_model=UploadResponse)
async def upload_photos(
    files: List[UploadFile],
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage_root: str = Depends(get_photo_storage_root),
) -> UploadResponse:
    # 50-file cap
    if len(files) > _MAX_FILES:
        raise HTTPException(status_code=413, detail=f"Too many files: max {_MAX_FILES} per request")

    # Pre-flight: count existing staging rows
    count_result = await db.execute(
        select(func.count()).where(StagingPhotoTable.user_id == user.id)
    )
    existing_count = count_result.scalar_one()

    if existing_count >= _STAGING_CAP:
        raise HTTPException(
            status_code=429,
            detail="Inbox full — group or discard photos before uploading more.",
        )

    # Check if adding these files would exceed the cap
    if existing_count + len(files) > _STAGING_CAP:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Inbox is nearly full — you have {existing_count} staging photos. "
                "Group or discard some before uploading more."
            ),
        )

    root = Path(storage_root)
    staging_dir = root / "staging" / str(user.id)
    staging_dir.mkdir(parents=True, exist_ok=True)

    succeeded: list[StagingPhotoOut] = []
    failed: list[UploadFailure] = []

    for upload in files:
        filename = upload.filename or "upload"
        try:
            # Read with size limit
            data = await upload.read(_MAX_PER_FILE_BYTES + 1)
            if len(data) > _MAX_PER_FILE_BYTES:
                failed.append(UploadFailure(
                    original_filename=filename,
                    reason=f"File is too large; maximum is 25 MB per file.",
                ))
                continue

            full_jpeg, thumb_jpeg, captured_at = process_photo(data, filename)

            # Write files first, then DB row
            file_id = str(uuid.uuid4())
            full_path = staging_dir / f"{file_id}.jpg"
            thumb_path = staging_dir / f"{file_id}.thumb.jpg"

            full_path.write_bytes(full_jpeg)
            thumb_path.write_bytes(thumb_jpeg)

            storage_key = f"staging/{user.id}/{file_id}.jpg"
            thumbnail_key = f"staging/{user.id}/{file_id}.thumb.jpg"

            row = StagingPhotoTable(
                user_id=user.id,
                storage_key=storage_key,
                thumbnail_key=thumbnail_key,
                original_filename=filename,
                captured_at=captured_at,
            )
            db.add(row)
            await db.flush()

            succeeded.append(StagingPhotoOut(
                id=row.id,
                thumbnail_url=_thumbnail_url(thumbnail_key),
                original_filename=filename,
                captured_at=captured_at,
            ))

        except FileTooLargeError as e:
            failed.append(UploadFailure(original_filename=filename, reason=str(e)))
        except UnsupportedFormatError:
            failed.append(UploadFailure(
                original_filename=filename,
                reason="Unsupported format — please upload JPEG, PNG, HEIC/HEIF, or WebP.",
            ))
        except Exception as e:
            logger.exception("Unexpected error processing %s", filename)
            failed.append(UploadFailure(original_filename=filename, reason=f"Processing error: {e}"))

    await db.commit()
    return UploadResponse(succeeded=succeeded, failed=failed)


# ---------------------------------------------------------------------------
# GET /upload/staging
# ---------------------------------------------------------------------------

@router.get("/staging", response_model=StagingListResponse)
async def get_staging(
    limit: int = 200,
    before: Optional[int] = None,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StagingListResponse:
    limit = min(limit, 200)

    query = select(StagingPhotoTable).where(StagingPhotoTable.user_id == user.id)
    if before is not None:
        query = query.where(StagingPhotoTable.id < before)
    query = query.order_by(StagingPhotoTable.id.desc()).limit(limit + 1)

    result = await db.execute(query)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    photos = [
        StagingPhotoOut(
            id=r.id,
            thumbnail_url=_thumbnail_url(r.thumbnail_key or ""),
            original_filename=r.original_filename,
            captured_at=r.captured_at,
        )
        for r in rows
    ]
    return StagingListResponse(photos=photos, has_more=has_more)


# ---------------------------------------------------------------------------
# POST /upload/group
# ---------------------------------------------------------------------------

@router.post("/group", response_model=GroupResponse)
async def group_photos(
    body: GroupRequest,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage_root: str = Depends(get_photo_storage_root),
) -> GroupResponse:
    # 1. Validate collection ownership (404 to avoid existence oracle)
    await _require_collection_owner_404(db, body.collection_id, user.id)

    # 2. Validate all photo IDs belong to this user
    result = await db.execute(
        select(StagingPhotoTable).where(
            StagingPhotoTable.id.in_(body.photo_ids),
            StagingPhotoTable.user_id == user.id,
        )
    )
    staging_rows = result.scalars().all()
    if len(staging_rows) != len(body.photo_ids):
        raise HTTPException(status_code=404, detail="One or more photos not found")

    # Build ordered list matching requested photo_ids order
    row_by_id = {r.id: r for r in staging_rows}
    ordered_rows = [row_by_id[pid] for pid in body.photo_ids]

    # 3. Atomic DB transaction: create item + photo rows + delete staging rows
    item = ItemTable(
        collection_id=body.collection_id,
        brand="unknown",
        description="",
        status="undecided",
    )
    db.add(item)
    await db.flush()

    photo_rows = []
    for i, staging in enumerate(ordered_rows):
        photo = ItemPhotoTable(
            item_id=item.id,
            storage_key=staging.storage_key,
            thumbnail_key=staging.thumbnail_key,
            is_hero=(i == 0),
            sort_order=i,
            captured_at=staging.captured_at,
        )
        db.add(photo)
        photo_rows.append(photo)

    # Delete staging rows
    await db.execute(
        delete(StagingPhotoTable).where(
            StagingPhotoTable.id.in_(body.photo_ids)
        )
    )

    await db.commit()

    # Refresh photo rows to get their IDs and current storage_keys
    for photo in photo_rows:
        await db.refresh(photo)

    # 4. Post-commit: attempt file renames
    root = Path(storage_root)
    for photo, staging in zip(photo_rows, ordered_rows):
        src = root / staging.storage_key
        new_dir = root / "collections" / str(body.collection_id) / "items" / str(item.id)
        new_dir.mkdir(parents=True, exist_ok=True)
        dst = new_dir / Path(staging.storage_key).name

        # Thumbnail rename too
        thumb_src = root / staging.thumbnail_key if staging.thumbnail_key else None
        thumb_dst = new_dir / Path(staging.thumbnail_key).name if staging.thumbnail_key else None

        try:
            os.rename(str(src), str(dst))
            new_key = str(dst.relative_to(root))
            photo.storage_key = new_key

            if thumb_src and thumb_dst and thumb_src.exists():
                os.rename(str(thumb_src), str(thumb_dst))
                photo.thumbnail_key = str(thumb_dst.relative_to(root))

            await db.commit()
        except OSError as e:
            logger.warning("File rename failed for photo %s: %s; leaving at staging path", photo.id, e)
            await db.rollback()

    return GroupResponse(item_id=item.id)


# ---------------------------------------------------------------------------
# DELETE /upload/staging/{staging_id}
# ---------------------------------------------------------------------------

@router.delete("/staging/{staging_id}", status_code=204)
async def discard_staging(
    staging_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage_root: str = Depends(get_photo_storage_root),
) -> None:
    result = await db.execute(
        select(StagingPhotoTable).where(
            StagingPhotoTable.id == staging_id,
            StagingPhotoTable.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Staging photo not found")

    root = Path(storage_root)

    # Delete files (idempotent — ignore FileNotFoundError)
    for key in (row.storage_key, row.thumbnail_key):
        if key:
            try:
                (root / key).unlink()
            except FileNotFoundError:
                pass

    # Delete DB row
    await db.execute(
        delete(StagingPhotoTable).where(StagingPhotoTable.id == staging_id)
    )
    await db.commit()
