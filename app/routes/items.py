from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import CollectionTable, ItemRead, ItemTable, UserTable

router = APIRouter()


async def _require_collection_owner(db: AsyncSession, collection_id: int, user_id: int) -> CollectionTable:
    result = await db.execute(
        select(CollectionTable).where(CollectionTable.id == collection_id)
    )
    coll = result.scalar_one_or_none()
    if coll is None or coll.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return coll


class ItemCreateBody(BaseModel):
    brand: str = "unknown"
    description: str = ""
    condition_score: Optional[float] = None
    status: str = "undecided"
    primary_color: Optional[Literal[
        "red", "yellow", "orange", "green", "blue", "violet",
        "white", "black", "tan", "brown", "multi"
    ]] = None
    secondary_colors: list[Literal[
        "red", "yellow", "orange", "green", "blue", "violet",
        "white", "black", "tan", "brown", "multi"
    ]] = Field(default_factory=list)
    style: Optional[Literal[
        "satchel", "saddlebag", "duffel", "frame", "messenger", "tote",
        "foldover", "barrel", "bucket", "hobo", "baguette", "doctor",
        "backpack", "clutch", "envelope", "minaudiere", "crossbody",
        "diaper", "wristlet", "belt-bag"
    ]] = None
    material: Optional[Literal[
        "leather", "vegan leather", "cloth", "tapestry", "velvet", "suede", "performance"
    ]] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    depth_in: Optional[float] = None
    serial_number: Optional[str] = None
    asking_price: Optional[int] = None

    @model_validator(mode="after")
    def check_multi_color_exclusion(self) -> "ItemCreateBody":
        if self.primary_color == "multi" and self.secondary_colors:
            raise ValueError(
                "When primary_color is 'multi', secondary_colors must be empty."
            )
        return self


class ItemUpdateBody(BaseModel):
    brand: Optional[str] = None
    description: Optional[str] = None
    condition_score: Optional[float] = None
    status: Optional[str] = None
    primary_color: Optional[Literal[
        "red", "yellow", "orange", "green", "blue", "violet",
        "white", "black", "tan", "brown", "multi"
    ]] = None
    secondary_colors: Optional[list[Literal[
        "red", "yellow", "orange", "green", "blue", "violet",
        "white", "black", "tan", "brown", "multi"
    ]]] = None
    style: Optional[Literal[
        "satchel", "saddlebag", "duffel", "frame", "messenger", "tote",
        "foldover", "barrel", "bucket", "hobo", "baguette", "doctor",
        "backpack", "clutch", "envelope", "minaudiere", "crossbody",
        "diaper", "wristlet", "belt-bag"
    ]] = None
    material: Optional[Literal[
        "leather", "vegan leather", "cloth", "tapestry", "velvet", "suede", "performance"
    ]] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    depth_in: Optional[float] = None
    serial_number: Optional[str] = None
    asking_price: Optional[int] = None

    @model_validator(mode="after")
    def check_multi_color_exclusion(self) -> "ItemUpdateBody":
        if self.primary_color == "multi" and self.secondary_colors:
            raise ValueError(
                "When primary_color is 'multi', secondary_colors must be empty."
            )
        return self


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
        primary_color=body.primary_color,
        secondary_colors=body.secondary_colors,
        style=body.style,
        material=body.material,
        width_in=body.width_in,
        height_in=body.height_in,
        depth_in=body.depth_in,
        serial_number=body.serial_number,
        asking_price=body.asking_price,
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
    await _require_collection_owner(db, collection_id, user.id)
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
    await _require_collection_owner(db, collection_id, user.id)
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
    await _require_collection_owner(db, collection_id, user.id)

    result = await db.execute(
        select(ItemTable).where(
            ItemTable.id == item_id, ItemTable.collection_id == collection_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = body.model_dump(exclude_unset=True)

    # Auto-clear secondary_colors when primary_color is set to "multi",
    # preserving the mutual-exclusion invariant even when secondary_colors
    # is not included in this request body.
    if update_data.get("primary_color") == "multi":
        update_data["secondary_colors"] = []

    for key, value in update_data.items():
        setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    return ItemRead.model_validate(row)
