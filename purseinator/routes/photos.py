from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from purseinator.deps import get_current_user, get_db
from purseinator.models import ItemPhotoRead, ItemPhotoTable, ItemTable, UserTable

router = APIRouter()


def _storage_root(request: Request) -> str:
    return request.app.state.photo_storage_root


@router.post("/collections/{collection_id}/items/{item_id}/photos", status_code=201)
async def upload_photo(
    collection_id: int,
    item_id: int,
    file: UploadFile,
    request: Request,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemPhotoRead:
    item = await db.get(ItemTable, item_id)
    if item is None or item.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Item not found")

    storage_root = _storage_root(request)
    data = await file.read()

    storage_key = f"collections/{collection_id}/items/{item_id}/{file.filename}"
    path = Path(storage_root) / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    # First photo for this item becomes hero
    result = await db.execute(
        select(ItemPhotoTable).where(ItemPhotoTable.item_id == item_id)
    )
    existing = result.scalars().all()
    is_hero = len(existing) == 0

    row = ItemPhotoTable(
        item_id=item_id,
        storage_key=storage_key,
        is_hero=is_hero,
        sort_order=len(existing),
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
    result = await db.execute(
        select(ItemPhotoTable)
        .where(ItemPhotoTable.item_id == item_id)
        .order_by(ItemPhotoTable.sort_order)
    )
    return [ItemPhotoRead.model_validate(r) for r in result.scalars().all()]


@router.get("/photos/{storage_key:path}")
async def serve_photo(storage_key: str, request: Request):
    storage_root = _storage_root(request)
    path = Path(storage_root) / storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(path)
