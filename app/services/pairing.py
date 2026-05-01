def info_level_for_gap(elo_gap: float) -> str:
    """Determine how much info to reveal based on Elo gap between items."""
    if elo_gap > 200:
        return "photos_only"
    if elo_gap > 100:
        return "brand"
    if elo_gap >= 50:
        return "condition"
    return "price"


def select_pair(
    ratings: list[tuple[int, float, int]],
) -> tuple[int, int]:
    """Select a pair for comparison. Prefers similar ratings and undercompared items.

    ratings: list of (item_id, elo_rating, comparison_count)
    Returns: (item_a_id, item_b_id)
    """
    sorted_by_count = sorted(ratings, key=lambda r: r[2])
    pool_size = min(max(len(sorted_by_count) // 2, 2), len(sorted_by_count))
    pool = sorted_by_count[:pool_size]
    pool.sort(key=lambda r: r[1])
    best_gap = float("inf")
    best_pair = (pool[0][0], pool[1][0])
    for i in range(len(pool) - 1):
        gap = abs(pool[i][1] - pool[i + 1][1])
        if gap < best_gap:
            best_gap = gap
            best_pair = (pool[i][0], pool[i + 1][0])
    return best_pair
