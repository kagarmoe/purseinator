import pytest
from app.services.elo import calculate_new_ratings, expected_score, k_factor_for_item


def test_expected_score_equal_ratings():
    score = expected_score(1500, 1500)
    assert score == pytest.approx(0.5)


def test_expected_score_higher_rated_favored():
    score = expected_score(1600, 1400)
    assert score > 0.5


def test_calculate_new_ratings_winner_gains():
    winner_new, loser_new = calculate_new_ratings(
        winner_rating=1500, loser_rating=1500, k_factor=32,
    )
    assert winner_new > 1500
    assert loser_new < 1500


def test_calculate_new_ratings_sum_preserved():
    winner_new, loser_new = calculate_new_ratings(1500, 1500, k_factor=32)
    assert winner_new + loser_new == pytest.approx(3000)


def test_k_factor_decreases_with_comparisons():
    assert k_factor_for_item(comparison_count=0) == 32
    assert k_factor_for_item(comparison_count=10) < 32
    assert k_factor_for_item(comparison_count=30) < k_factor_for_item(comparison_count=10)


def test_larger_upset_produces_larger_rating_change():
    big_winner_new, _ = calculate_new_ratings(1200, 1800, k_factor=32)
    small_winner_new, _ = calculate_new_ratings(1490, 1510, k_factor=32)
    big_change = big_winner_new - 1200
    small_change = small_winner_new - 1490
    assert big_change > small_change
