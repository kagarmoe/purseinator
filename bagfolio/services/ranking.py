from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bagfolio.models import (
    ComparisonTable,
    EloRatingTable,
    ItemRead,
    ItemTable,
)
from bagfolio.services.elo import calculate_new_ratings, k_factor_for_item
from bagfolio.services.pairing import info_level_for_gap, select_pair


async def ensure_ratings(db: AsyncSession, collection_id: int, user_id: int) -> None:
    """Create EloRating records (1500) for items that don't have one yet."""
    items = await db.execute(
        select(ItemTable.id).where(ItemTable.collection_id == collection_id)
    )
    item_ids = [row[0] for row in items.all()]

    existing = await db.execute(
        select(EloRatingTable.item_id).where(
            EloRatingTable.collection_id == collection_id,
            EloRatingTable.user_id == user_id,
        )
    )
    existing_ids = {row[0] for row in existing.all()}

    for item_id in item_ids:
        if item_id not in existing_ids:
            db.add(
                EloRatingTable(
                    item_id=item_id,
                    collection_id=collection_id,
                    user_id=user_id,
                    rating=1500.0,
                    comparison_count=0,
                )
            )
    await db.flush()


async def get_next_pair(
    db: AsyncSession, collection_id: int, user_id: int
) -> dict:
    await ensure_ratings(db, collection_id, user_id)

    result = await db.execute(
        select(EloRatingTable).where(
            EloRatingTable.collection_id == collection_id,
            EloRatingTable.user_id == user_id,
        )
    )
    ratings = result.scalars().all()
    rating_tuples = [(r.item_id, r.rating, r.comparison_count) for r in ratings]

    item_a_id, item_b_id = select_pair(rating_tuples)

    rating_a = next(r for r in ratings if r.item_id == item_a_id)
    rating_b = next(r for r in ratings if r.item_id == item_b_id)
    gap = abs(rating_a.rating - rating_b.rating)
    info_level = info_level_for_gap(gap)

    item_a = await db.get(ItemTable, item_a_id)
    item_b = await db.get(ItemTable, item_b_id)

    return {
        "item_a": ItemRead.model_validate(item_a),
        "item_b": ItemRead.model_validate(item_b),
        "info_level": info_level,
    }


async def record_comparison(
    db: AsyncSession,
    collection_id: int,
    user_id: int,
    item_a_id: int,
    item_b_id: int,
    winner_id: int,
    info_level_shown: str,
) -> None:
    await ensure_ratings(db, collection_id, user_id)

    rating_a = (
        await db.execute(
            select(EloRatingTable).where(
                EloRatingTable.item_id == item_a_id,
                EloRatingTable.collection_id == collection_id,
                EloRatingTable.user_id == user_id,
            )
        )
    ).scalar_one()

    rating_b = (
        await db.execute(
            select(EloRatingTable).where(
                EloRatingTable.item_id == item_b_id,
                EloRatingTable.collection_id == collection_id,
                EloRatingTable.user_id == user_id,
            )
        )
    ).scalar_one()

    if winner_id == item_a_id:
        k = k_factor_for_item(rating_a.comparison_count)
        new_a, new_b = calculate_new_ratings(rating_a.rating, rating_b.rating, k)
    else:
        k = k_factor_for_item(rating_b.comparison_count)
        new_b, new_a = calculate_new_ratings(rating_b.rating, rating_a.rating, k)

    rating_a.rating = new_a
    rating_a.comparison_count += 1
    rating_b.rating = new_b
    rating_b.comparison_count += 1

    db.add(
        ComparisonTable(
            collection_id=collection_id,
            user_id=user_id,
            item_a_id=item_a_id,
            item_b_id=item_b_id,
            winner_id=winner_id,
            info_level_shown=info_level_shown,
        )
    )
    await db.flush()


async def get_ranked_items(
    db: AsyncSession, collection_id: int, user_id: int
) -> list[dict]:
    await ensure_ratings(db, collection_id, user_id)

    result = await db.execute(
        select(EloRatingTable)
        .where(
            EloRatingTable.collection_id == collection_id,
            EloRatingTable.user_id == user_id,
        )
        .order_by(EloRatingTable.rating.desc())
    )
    ratings = result.scalars().all()

    ranked = []
    for r in ratings:
        item = await db.get(ItemTable, r.item_id)
        ranked.append(
            {
                **ItemRead.model_validate(item).model_dump(),
                "rating": r.rating,
                "comparison_count": r.comparison_count,
            }
        )
    return ranked
