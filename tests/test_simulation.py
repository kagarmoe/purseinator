from simulations.elo_convergence import simulate, kendall_tau_distance


def test_simulate_returns_results():
    results = simulate(num_items=10, comparisons_per_session=5, num_sessions=3)
    assert "sessions" in results
    assert "final_correlation" in results
    assert len(results["sessions"]) == 3


def test_simulate_correlation_improves():
    results = simulate(num_items=10, comparisons_per_session=10, num_sessions=5)
    first = results["sessions"][0]["correlation"]
    last = results["sessions"][-1]["correlation"]
    assert last >= first  # correlation should improve or stay same


def test_kendall_tau_perfect():
    assert kendall_tau_distance([1, 2, 3, 4], [1, 2, 3, 4]) == 1.0


def test_kendall_tau_reversed():
    assert kendall_tau_distance([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
