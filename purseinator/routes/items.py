from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from purseinator.deps import get_current_user, get_db
from purseinator.models import ItemRead, ItemTable, UserTable

router = APIRouter()


class ItemCreateBody(BaseModel):
    brand: str = "unknown"
    description: str = ""
    condition_score: Optional[float] = None
    status: str = "undecided"


class ItemUpdateBody(BaseModel):
    brand: Optional[str] = None
    description: Optional[str] = None
    condition_score: Optional[float] = None
    status: Optional[str] = None


@router.post("", status_code=201)
async def create_item(
    collection_id: int,
    body: ItemCreateBody,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemRead:
    row = ItemTable(
        collection_id=collection_id,
        brand=body.brand,
        description=body.description,
        condition_score=body.condition_score,
        status=body.status,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ItemRead.model_validate(row)


@router.get("")
async def list_items(
    collection_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ItemRead]:
    result = await db.execute(
        select(ItemTable).where(ItemTable.collection_id == collection_id)
    )
    return [ItemRead.model_validate(r) for r in result.scalars().all()]


@router.get("/{item_id}")
async def get_item(
    collection_id: int,
    item_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemRead:
    result = await db.execute(
        select(ItemTable).where(
            ItemTable.id == item_id, ItemTable.collection_id == collection_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemRead.model_validate(row)


@router.patch("/{item_id}")
async def update_item(
    collection_id: int,
    item_id: int,
    body: ItemUpdateBody,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemRead:
    result = await db.execute(
        select(ItemTable).where(
            ItemTable.id == item_id, ItemTable.collection_id == collection_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    return ItemRead.model_validate(row)
