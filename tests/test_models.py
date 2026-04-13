from __future__ import annotations

import pytest

from bagfolio.models import (
    CollectionCreate,
    ComparisonCreate,
    ItemCreate,
    UserCreate,
)


def test_user_create_valid_curator():
    user = UserCreate(email="rachel@example.com", name="Rachel", role="curator")
    assert user.role == "curator"


def test_user_create_valid_operator():
    user = UserCreate(email="kim@example.com", name="Kim", role="operator")
    assert user.role == "operator"


def test_user_create_invalid_role():
    with pytest.raises(ValueError):
        UserCreate(email="x@x.com", name="X", role="admin")


def test_user_create_is_frozen():
    user = UserCreate(email="rachel@example.com", name="Rachel", role="curator")
    with pytest.raises(Exception):
        user.name = "Changed"


def test_item_create_unknown_brand():
    item = ItemCreate(collection_id=1, brand="unknown")
    assert item.brand == "unknown"


def test_item_create_defaults():
    item = ItemCreate(collection_id=1)
    assert item.brand == "unknown"
    assert item.status == "undecided"


def test_item_create_invalid_status():
    with pytest.raises(ValueError):
        ItemCreate(collection_id=1, status="deleted")


def test_collection_create_with_dollar_goal():
    coll = CollectionCreate(name="Rachel's Bags", dollar_goal=5000.0)
    assert coll.dollar_goal == 5000.0


def test_collection_create_dollar_goal_nullable():
    coll = CollectionCreate(name="Rachel's Bags")
    assert coll.dollar_goal is None


def test_comparison_create():
    comp = ComparisonCreate(
        collection_id=1,
        user_id=1,
        item_a_id=1,
        item_b_id=2,
        winner_id=1,
        info_level_shown="photos_only",
    )
    assert comp.winner_id in (comp.item_a_id, comp.item_b_id)


def test_comparison_create_invalid_info_level():
    with pytest.raises(ValueError):
        ComparisonCreate(
            collection_id=1,
            user_id=1,
            item_a_id=1,
            item_b_id=2,
            winner_id=1,
            info_level_shown="invalid",
        )
