from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import CollectionTable, UserTable
from app.services.ranking import get_next_pair, get_ranked_items, record_comparison

router = APIRouter()


class CompareRequest(BaseModel):
    item_a_id: int
    item_b_id: int
    winner_id: int
    info_level_shown: str

    @model_validator(mode="after")
    def winner_must_be_in_pair(self) -> "CompareRequest":
        if self.item_a_id == self.item_b_id:
            raise ValueError("item_a_id and item_b_id must differ")
        if self.winner_id not in (self.item_a_id, self.item_b_id):
            raise ValueError("winner_id must be item_a_id or item_b_id")
        return self


async def _require_collection_owner(db: AsyncSession, collection_id: int, user_id: int) -> None:
    result = await db.execute(
        select(CollectionTable).where(CollectionTable.id == collection_id)
    )
    coll = result.scalar_one_or_none()
    if coll is None or coll.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/next")
async def next_pair(
    collection_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_collection_owner(db, collection_id, user.id)
    pair = await get_next_pair(db, collection_id, user.id)
    await db.commit()
    if pair is None:
        raise HTTPException(status_code=404, detail="Not enough items to compare")
    return {
        "item_a": pair["item_a"].model_dump(),
        "item_b": pair["item_b"].model_dump(),
        "info_level": pair["info_level"],
    }


@router.post("/compare", status_code=201)
async def submit_comparison(
    collection_id: int,
    body: CompareRequest,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_collection_owner(db, collection_id, user.id)
    await record_comparison(
        db,
        collection_id=collection_id,
        user_id=user.id,
        item_a_id=body.item_a_id,
        item_b_id=body.item_b_id,
        winner_id=body.winner_id,
        info_level_shown=body.info_level_shown,
    )
    await db.commit()
    return {"status": "recorded"}


@router.get("")
async def ranked_list(
    collection_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_collection_owner(db, collection_id, user.id)
    items = await get_ranked_items(db, collection_id, user.id)
    await db.commit()
    return items
