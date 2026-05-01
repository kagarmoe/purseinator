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
