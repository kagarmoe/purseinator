import pytest
from app.services.pairing import select_pair, info_level_for_gap


def test_select_pair_prefers_similar_ratings():
    ratings = [
        (1, 1500, 0), (2, 1510, 0), (3, 1200, 0), (4, 1800, 0),
    ]
    a, b = select_pair(ratings)
    assert {a, b} == {1, 2}


def test_select_pair_avoids_overcompared_items():
    ratings = [
        (1, 1500, 50), (2, 1510, 50), (3, 1490, 2), (4, 1505, 3),
    ]
    a, b = select_pair(ratings)
    assert {a, b} == {3, 4}


def test_info_level_photos_only():
    assert info_level_for_gap(250) == "photos_only"


def test_info_level_brand():
    assert info_level_for_gap(150) == "brand"


def test_info_level_condition():
    assert info_level_for_gap(75) == "condition"


def test_info_level_price():
    assert info_level_for_gap(30) == "price"


def test_select_pair_single_item_raises():
    with pytest.raises((IndexError, ValueError)):
        select_pair([(1, 1500, 0)])
