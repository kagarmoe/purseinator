import math


def expected_score(rating_a: float, rating_b: float) -> float:
    """Calculate the expected score of player A against player B."""
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))


def k_factor_for_item(comparison_count: int) -> float:
    """K starts at 32, decays toward 16 as item gets more comparisons."""
    return max(16, 32 * math.exp(-comparison_count / 20))


def calculate_new_ratings(
    winner_rating: float, loser_rating: float, k_factor: float,
) -> tuple[float, float]:
    """Calculate new Elo ratings after a comparison where winner beat loser."""
    expected_win = expected_score(winner_rating, loser_rating)
    winner_new = winner_rating + k_factor * (1 - expected_win)
    loser_new = loser_rating + k_factor * (0 - (1 - expected_win))
    return winner_new, loser_new
