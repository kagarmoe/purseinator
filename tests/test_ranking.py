from __future__ import annotations

import pytest


@pytest.fixture
async def collection_with_items(auth_client):
    """Create a collection with 4 items for ranking tests."""
    resp = await auth_client.post("/collections", json={"name": "Ranking Test"})
    cid = resp.json()["id"]
    for brand in ("Coach", "Gucci", "Prada", "Chanel"):
        await auth_client.post(f"/collections/{cid}/items", json={"brand": brand})
    return cid


@pytest.mark.asyncio
async def test_get_next_pair(auth_client, collection_with_items):
    cid = collection_with_items
    resp = await auth_client.get(f"/collections/{cid}/ranking/next")
    assert resp.status_code == 200
    data = resp.json()
    assert "item_a" in data and "item_b" in data
    assert "info_level" in data
    assert data["item_a"]["id"] != data["item_b"]["id"]


@pytest.mark.asyncio
async def test_submit_comparison(auth_client, collection_with_items):
    cid = collection_with_items
    pair = (await auth_client.get(f"/collections/{cid}/ranking/next")).json()
    resp = await auth_client.post(
        f"/collections/{cid}/ranking/compare",
        json={
            "item_a_id": pair["item_a"]["id"],
            "item_b_id": pair["item_b"]["id"],
            "winner_id": pair["item_a"]["id"],
            "info_level_shown": pair["info_level"],
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_submit_comparison_updates_elo(auth_client, collection_with_items):
    cid = collection_with_items
    before = (await auth_client.get(f"/collections/{cid}/ranking")).json()
    pair = (await auth_client.get(f"/collections/{cid}/ranking/next")).json()
    await auth_client.post(
        f"/collections/{cid}/ranking/compare",
        json={
            "item_a_id": pair["item_a"]["id"],
            "item_b_id": pair["item_b"]["id"],
            "winner_id": pair["item_a"]["id"],
            "info_level_shown": pair["info_level"],
        },
    )
    after = (await auth_client.get(f"/collections/{cid}/ranking")).json()
    assert before != after


@pytest.mark.asyncio
async def test_get_ranked_list(auth_client, collection_with_items):
    cid = collection_with_items
    resp = await auth_client.get(f"/collections/{cid}/ranking")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 4
    ratings = [item["rating"] for item in items]
    assert ratings == sorted(ratings, reverse=True)


@pytest.mark.asyncio
async def test_ranked_list_includes_item_data(auth_client, collection_with_items):
    cid = collection_with_items
    resp = await auth_client.get(f"/collections/{cid}/ranking")
    item = resp.json()[0]
    assert "id" in item
    assert "brand" in item
    assert "rating" in item
    assert "comparison_count" in item


@pytest.mark.asyncio
async def test_next_pair_single_item_returns_404(auth_client):
    resp = await auth_client.post("/collections", json={"name": "Solo"})
    cid = resp.json()["id"]
    await auth_client.post(f"/collections/{cid}/items", json={"brand": "Coach"})
    resp = await auth_client.get(f"/collections/{cid}/ranking/next")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_comparison_invalid_winner_returns_422(auth_client, collection_with_items):
    cid = collection_with_items
    pair = (await auth_client.get(f"/collections/{cid}/ranking/next")).json()
    resp = await auth_client.post(
        f"/collections/{cid}/ranking/compare",
        json={
            "item_a_id": pair["item_a"]["id"],
            "item_b_id": pair["item_b"]["id"],
            "winner_id": 99999,
            "info_level_shown": pair["info_level"],
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_multiple_comparisons(auth_client, collection_with_items):
    cid = collection_with_items
    for _ in range(5):
        pair = (await auth_client.get(f"/collections/{cid}/ranking/next")).json()
        await auth_client.post(
            f"/collections/{cid}/ranking/compare",
            json={
                "item_a_id": pair["item_a"]["id"],
                "item_b_id": pair["item_b"]["id"],
                "winner_id": pair["item_a"]["id"],
                "info_level_shown": pair["info_level"],
            },
        )
    ranked = (await auth_client.get(f"/collections/{cid}/ranking")).json()
    ratings = [r["rating"] for r in ranked]
    assert ratings == sorted(ratings, reverse=True)
    assert not all(r == 1500.0 for r in ratings)
