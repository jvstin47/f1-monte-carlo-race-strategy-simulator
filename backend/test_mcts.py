import pytest
from mcts_optimizer import MCTSSolver, MCTSState

def test_mcts_initialization():
    solver = MCTSSolver(
        track_id="bahrain",
        driver_id="ver",
        num_laps=57,
        base_lap_time=94.0,
        pit_stop_loss=22.0,
        available_compounds=["soft", "medium", "hard"],
        max_stops=2,
        sc_prob=0.04,
        risk_aversion=0.0,
        weather_enabled=False,
        driver_pace_offset=-0.15,
        driver_consistency=0.08,
        track_evolution_rate=0.02
    )
    assert solver.track_id == "bahrain"
    assert solver.driver_pace_offset == -0.15

def test_mcts_search():
    solver = MCTSSolver(
        track_id="bahrain",
        driver_id="ver",
        num_laps=5, # Tiny race for fast test
        base_lap_time=94.0,
        pit_stop_loss=22.0,
        available_compounds=["soft", "medium", "hard"],
        max_stops=2,
        sc_prob=0.04,
        risk_aversion=0.0,
        weather_enabled=False,
        driver_pace_offset=-0.15,
        driver_consistency=0.08,
        track_evolution_rate=0.02
    )
    
    state = MCTSState(lap=1, compound="soft", tire_age=1, weather_state="dry", is_sc_active=False, stops_made=0)
    solver.search(state, budget=10) # very small budget
    
    best_action = solver.get_best_action()
    assert best_action in ["stay_out", "pit_soft", "pit_medium", "pit_hard"]
    
    tree_data = solver.get_decision_tree_data()
    assert "state_description" in tree_data
    assert len(tree_data["candidates"]) > 0

def test_mcts_replan():
    # Test replanning midway through a race
    solver = MCTSSolver(
        track_id="bahrain",
        driver_id="generic",
        num_laps=57,
        base_lap_time=94.0,
        pit_stop_loss=22.0,
        available_compounds=["soft", "medium", "hard"],
        max_stops=2,
        sc_prob=0.0,
        risk_aversion=0.0,
        weather_enabled=False,
        driver_pace_offset=0.0,
        driver_consistency=0.15,
        track_evolution_rate=0.02
    )
    
    state = MCTSState(lap=20, compound="medium", tire_age=20, weather_state="dry", is_sc_active=False, stops_made=0)
    solver.search(state, budget=20)
    
    act = solver.get_best_action()
    # at lap 20 on a 20 lap old medium, it might pit or stay out.
    assert act is not None
