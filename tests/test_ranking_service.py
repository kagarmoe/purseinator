from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from purseinator.models import Base, CollectionTable, EloRatingTable, ItemTable, UserTable
from purseinator.services.ranking import ensure_ratings, get_ranked_items


@pytest.fixture
async def db_with_user_and_collection():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        user = UserTable(email="test@example.com", name="Test", role="curator")
        db.add(user)
        await db.flush()
        coll = CollectionTable(owner_id=user.id, name="Test Collection")
        db.add(coll)
        await db.flush()
        yield db, user.id, coll.id
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_ranked_items_sorted_by_rating_descending(db_with_user_and_collection):
    db, user_id, coll_id = db_with_user_and_collection
    for brand, rating in [("A", 1600.0), ("B", 1400.0), ("C", 1550.0)]:
        item = ItemTable(collection_id=coll_id, brand=brand)
        db.add(item)
        await db.flush()
        db.add(EloRatingTable(
            item_id=item.id, collection_id=coll_id, user_id=user_id,
            rating=rating, comparison_count=0
        ))
    await db.commit()

    ranked = await get_ranked_items(db, coll_id, user_id)
    ratings = [r["rating"] for r in ranked]
    assert ratings == sorted(ratings, reverse=True)
    assert ratings[0] == 1600.0


@pytest.mark.asyncio
async def test_ensure_ratings_creates_missing_elo_rows(db_with_user_and_collection):
    db, user_id, coll_id = db_with_user_and_collection
    item = ItemTable(collection_id=coll_id, brand="Coach")
    db.add(item)
    await db.commit()

    await ensure_ratings(db, coll_id, user_id)
    await db.commit()

    result = await db.execute(
        select(EloRatingTable).where(
            EloRatingTable.collection_id == coll_id,
            EloRatingTable.user_id == user_id,
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].rating == 1500.0
