"""Elo convergence simulation for Purseinator.

Simulates repeated pairwise comparisons against hidden true preferences
and measures how quickly Elo rankings converge to the true ranking.
"""

import argparse
import random
import sys
import os

# Add project root to path so we can import purseinator modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.elo import calculate_new_ratings, k_factor_for_item
from app.services.pairing import select_pair


def kendall_tau_distance(ranking_a: list, ranking_b: list) -> float:
    """Compute Kendall tau correlation between two rankings.

    Returns a value in [-1, 1] where:
      1.0 = perfect agreement
     -1.0 = perfect disagreement (reversed)
      0.0 = no correlation
    """
    n = len(ranking_a)
    if n < 2:
        return 1.0

    # Build order mappings: for each list, map value -> position
    order_a = {v: i for i, v in enumerate(ranking_a)}
    order_b = {v: i for i, v in enumerate(ranking_b)}

    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            a_i, a_j = ranking_a[i], ranking_a[j]
            # Compare relative order: does pair (a_i, a_j) have same
            # relative order in both rankings?
            diff_a = order_a[a_i] - order_a[a_j]
            diff_b = order_b[a_i] - order_b[a_j]
            if diff_a * diff_b > 0:
                concordant += 1
            elif diff_a * diff_b < 0:
                discordant += 1
            # ties (diff == 0) are ignored

    total_pairs = n * (n - 1) // 2
    if total_pairs == 0:
        return 1.0
    return (concordant - discordant) / total_pairs


def simulate(
    num_items: int = 50,
    comparisons_per_session: int = 10,
    num_sessions: int = 10,
    noise: float = 0.10,
    seed: int | None = None,
) -> dict:
    """Run an Elo convergence simulation.

    Args:
        num_items: Number of items in the collection.
        comparisons_per_session: Pairwise comparisons per session.
        num_sessions: Number of sessions to simulate.
        noise: Probability of picking the lower-preference item (upset).
        seed: Random seed for reproducibility.

    Returns:
        Dictionary with session-by-session results and final correlation.
    """
    rng = random.Random(seed)

    # Assign hidden true preference scores (higher = better)
    true_scores = {i: rng.random() for i in range(num_items)}

    # True ranking: item ids sorted by true score descending
    true_ranking = sorted(true_scores, key=lambda x: true_scores[x], reverse=True)

    # Initialize Elo state
    elo_ratings = {i: 1500.0 for i in range(num_items)}
    comparison_counts = {i: 0 for i in range(num_items)}

    session_results = []

    for session_idx in range(num_sessions):
        for _ in range(comparisons_per_session):
            # Build ratings list for select_pair: (item_id, elo_rating, comparison_count)
            ratings_list = [
                (item_id, elo_ratings[item_id], comparison_counts[item_id])
                for item_id in range(num_items)
            ]

            item_a, item_b = select_pair(ratings_list)

            # Simulate Rachel's choice based on true preference + noise
            if true_scores[item_a] > true_scores[item_b]:
                winner, loser = item_a, item_b
            else:
                winner, loser = item_b, item_a

            # Apply noise: with probability `noise`, flip the outcome
            if rng.random() < noise:
                winner, loser = loser, winner

            # Update Elo ratings
            k = k_factor_for_item(
                min(comparison_counts[winner], comparison_counts[loser])
            )
            new_winner, new_loser = calculate_new_ratings(
                elo_ratings[winner], elo_ratings[loser], k
            )
            elo_ratings[winner] = new_winner
            elo_ratings[loser] = new_loser
            comparison_counts[winner] += 1
            comparison_counts[loser] += 1

        # Compute Elo ranking after this session
        elo_ranking = sorted(
            elo_ratings, key=lambda x: elo_ratings[x], reverse=True
        )

        correlation = kendall_tau_distance(true_ranking, elo_ranking)

        total_comparisons = sum(comparison_counts.values()) // 2
        session_results.append(
            {
                "session": session_idx + 1,
                "total_comparisons": total_comparisons,
                "correlation": correlation,
            }
        )

    return {
        "num_items": num_items,
        "comparisons_per_session": comparisons_per_session,
        "num_sessions": num_sessions,
        "noise": noise,
        "sessions": session_results,
        "final_correlation": session_results[-1]["correlation"],
    }


def main():
    parser = argparse.ArgumentParser(description="Elo convergence simulation")
    parser.add_argument("--items", type=int, default=50, help="Number of items")
    parser.add_argument("--sessions", type=int, default=10, help="Number of sessions")
    parser.add_argument(
        "--comparisons", type=int, default=None,
        help="Comparisons per session (default: items // 2)",
    )
    parser.add_argument("--noise", type=float, default=0.10, help="Upset probability")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    comparisons = args.comparisons if args.comparisons else args.items // 2

    results = simulate(
        num_items=args.items,
        comparisons_per_session=comparisons,
        num_sessions=args.sessions,
        noise=args.noise,
        seed=args.seed,
    )

    print(f"Elo Convergence Simulation")
    print(f"  Items: {results['num_items']}")
    print(f"  Comparisons/session: {results['comparisons_per_session']}")
    print(f"  Sessions: {results['num_sessions']}")
    print(f"  Noise: {results['noise']:.0%}")
    print()
    print(f"{'Session':>8}  {'Comparisons':>12}  {'Kendall tau':>12}")
    print(f"{'-------':>8}  {'----------':>12}  {'-----------':>12}")
    for s in results["sessions"]:
        print(f"{s['session']:>8}  {s['total_comparisons']:>12}  {s['correlation']:>12.4f}")
    print()
    print(f"Final correlation: {results['final_correlation']:.4f}")


if __name__ == "__main__":
    main()
