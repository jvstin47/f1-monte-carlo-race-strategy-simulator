from mcts_optimizer import MCTSSolver, MCTSState


def _make_solver(**overrides):
    params = dict(
        track_id="bahrain", driver_id="generic", num_laps=57, base_lap_time=94.0,
        pit_stop_loss=22.0, available_compounds=["soft", "medium", "hard"], max_stops=2,
        sc_prob=0.04, risk_aversion=0.0, weather_enabled=True, driver_pace_offset=0.0,
        driver_consistency=0.15, track_evolution_rate=0.02, rollout_num_simulations=100,
    )
    params.update(overrides)
    return MCTSSolver(**params)


def test_hybrid_mode_uses_both_evaluation_paths():
    solver = _make_solver(use_hybrid_evaluation=True)
    state = MCTSState(lap=1, compound="medium", tire_age=1, weather_state="dry", is_sc_active=False, stops_made=0)
    solver.search(state, budget=150)
    stats = solver.get_search_stats()
    assert stats["nodes_created"] > 0
    assert stats["heuristic_evaluations"] > 0, "hybrid mode should use the cheap heuristic for at least some leaves"
    assert stats["high_fidelity_rollouts"] > 0, "hybrid mode should still escalate on some triggers"
    assert stats["heuristic_evaluations"] + stats["high_fidelity_rollouts"] == stats["nodes_created"]


def test_classic_mode_always_uses_high_fidelity():
    # use_hybrid_evaluation=False reproduces the original (v4) behavior: every
    # leaf gets a real rollout. This is the baseline evaluate_mcts.py compares
    # the hybrid solver against.
    solver = _make_solver(use_hybrid_evaluation=False)
    state = MCTSState(lap=1, compound="medium", tire_age=1, weather_state="dry", is_sc_active=False, stops_made=0)
    solver.search(state, budget=30)
    stats = solver.get_search_stats()
    assert stats["heuristic_evaluations"] == 0
    assert stats["high_fidelity_rollouts"] == stats["nodes_created"]


def test_late_race_always_escalates():
    solver = _make_solver(late_race_lap_threshold=10)
    state = MCTSState(lap=55, compound="medium", tire_age=5, weather_state="dry", is_sc_active=False, stops_made=1)
    use_hf, triggers = solver._should_use_high_fidelity(state, "stay_out")
    assert use_hf
    assert "late_race" in triggers


def test_ordinary_dry_stay_out_uses_cheap_heuristic():
    solver = _make_solver(late_race_lap_threshold=10)
    state = MCTSState(lap=5, compound="medium", tire_age=5, weather_state="dry", is_sc_active=False, stops_made=0)
    use_hf, triggers = solver._should_use_high_fidelity(state, "stay_out")
    assert not use_hf
    assert triggers == []


def test_pit_action_always_escalates():
    solver = _make_solver()
    state = MCTSState(lap=5, compound="medium", tire_age=5, weather_state="dry", is_sc_active=False, stops_made=0)
    use_hf, triggers = solver._should_use_high_fidelity(state, "pit_hard")
    assert use_hf
    assert "pit_stop" in triggers


def test_adaptive_refinement_adds_weighted_samples():
    solver = _make_solver()
    state = MCTSState(lap=1, compound="medium", tire_age=1, weather_state="dry", is_sc_active=False, stops_made=0)
    solver.search(state, budget=100)
    visits_before = {a: n.visit_count for a, n in solver.root.action_children.items()}

    solver.search(state, budget=0, refine_top_k=2, refine_sample_weight=3)
    visits_after = {a: n.visit_count for a, n in solver.root.action_children.items()}

    total_gained = sum(visits_after[a] - visits_before.get(a, 0) for a in visits_after)
    assert total_gained > 0
    stats = solver.get_search_stats()
    assert stats["trigger_counts"].get("adaptive_refinement", 0) > 0


def test_best_action_is_legal():
    solver = _make_solver()
    state = MCTSState(lap=1, compound="soft", tire_age=1, weather_state="dry", is_sc_active=False, stops_made=0)
    solver.search(state, budget=100, refine_top_k=1)
    act = solver.get_best_action()
    assert act in ["stay_out", "pit_medium", "pit_hard"]  # pit_soft excluded: already on soft


if __name__ == "__main__":
    test_hybrid_mode_uses_both_evaluation_paths()
    test_classic_mode_always_uses_high_fidelity()
    test_late_race_always_escalates()
    test_ordinary_dry_stay_out_uses_cheap_heuristic()
    test_pit_action_always_escalates()
    test_adaptive_refinement_adds_weighted_samples()
    test_best_action_is_legal()
    print("All hybrid MCTS tests passed.")
