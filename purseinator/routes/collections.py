from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from purseinator.deps import get_current_user, get_db
from purseinator.models import CollectionCreate, CollectionRead, CollectionTable, UserTable

router = APIRouter()


@router.post("", status_code=201)
async def create_collection(
    body: CollectionCreate,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollectionRead:
    row = CollectionTable(
        owner_id=user.id,
        name=body.name,
        description=body.description,
        dollar_goal=body.dollar_goal,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return CollectionRead.model_validate(row)


@router.get("")
async def list_collections(
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CollectionRead]:
    result = await db.execute(
        select(CollectionTable).where(CollectionTable.owner_id == user.id)
    )
    return [CollectionRead.model_validate(r) for r in result.scalars().all()]


@router.get("/{collection_id}")
async def get_collection(
    collection_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollectionRead:
    result = await db.execute(
        select(CollectionTable).where(CollectionTable.id == collection_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionRead.model_validate(row)
