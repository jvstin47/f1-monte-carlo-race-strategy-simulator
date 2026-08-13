import math

from calibration_harness import run_calibration, rank_correlation, heuristic_action_cost, real_action_cost
from mcts_optimizer import MCTSState, MCTSSolver


def test_rank_correlation_basics():
    assert math.isclose(rank_correlation([1, 2, 3], [1, 2, 3]), 1.0)
    assert math.isclose(rank_correlation([1, 2, 3], [3, 2, 1]), -1.0)
    assert math.isnan(rank_correlation([1, 1, 1], [1, 2, 3]))  # no variance in `a` -> undefined


def test_heuristic_cost_is_compound_agnostic():
    # Documents the exact defect Phase 1 measured: the traversal heuristic can't
    # distinguish which compound a pit stop switches to.
    state = MCTSState(lap=15, compound="medium", tire_age=15, weather_state="dry", is_sc_active=False, stops_made=0)
    cost_soft = heuristic_action_cost(state, "pit_soft", num_laps=57, base_lap_time=94.0, pit_stop_loss=22.0)
    cost_hard = heuristic_action_cost(state, "pit_hard", num_laps=57, base_lap_time=94.0, pit_stop_loss=22.0)
    assert cost_soft == cost_hard


def test_real_cost_is_compound_aware():
    # The real, simulator-grounded cost should NOT collapse soft and hard together.
    solver = MCTSSolver(
        track_id="bahrain", driver_id="generic", num_laps=57, base_lap_time=94.0,
        pit_stop_loss=22.0, available_compounds=["soft", "medium", "hard"], max_stops=2,
        sc_prob=0.04, risk_aversion=0.0, weather_enabled=False, driver_pace_offset=0.0,
        driver_consistency=0.15, track_evolution_rate=0.02, rollout_num_simulations=200,
    )
    state = MCTSState(lap=15, compound="medium", tire_age=15, weather_state="dry", is_sc_active=False, stops_made=0)
    cost_soft = real_action_cost(solver, state, "pit_soft")
    cost_hard = real_action_cost(solver, state, "pit_hard")
    assert cost_soft != cost_hard


def test_run_calibration_shape():
    results = run_calibration(track_id="bahrain", num_states=5, seed=1)
    summary = results["summary"]
    assert summary["num_states_sampled"] == 5
    assert summary["top1_agreement_rate_pct"] is None or 0.0 <= summary["top1_agreement_rate_pct"] <= 100.0
    assert len(results["per_state"]) == summary["num_states_evaluated"]
    for entry in results["per_state"]:
        assert len(entry["heuristic_costs"]) == len(entry["actions"])
        assert len(entry["real_costs"]) == len(entry["actions"])
        assert entry["heuristic_best"] in entry["actions"]
        assert entry["real_best"] in entry["actions"]


if __name__ == "__main__":
    test_rank_correlation_basics()
    test_heuristic_cost_is_compound_agnostic()
    test_real_cost_is_compound_aware()
    test_run_calibration_shape()
    print("All calibration harness tests passed.")
