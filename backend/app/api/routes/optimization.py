"""Dynamic Programming and MCTS strategy optimization routes."""

from fastapi import APIRouter
from ...models.optimization import OptimizeInput, OptimizeResponse
from ...models.mcts import MCTSRequest, MCTSResponse
from ...models.strategy import StrategyInput
from ...engine.dp_optimizer import optimize_strategy
from ...engine.simulator import simulate_strategy_vectorized, summarize_simulation
from ...engine.mcts.solver import MCTSSolver
from ...engine.mcts.state import MCTSState
from ...data.tracks import get_track
from ...data.drivers import get_driver
from ...core.exceptions import CircuitNotFoundError
from ..dependencies import resolve_track_params

router = APIRouter(tags=["Optimization"])


@router.post("/optimize", response_model=OptimizeResponse)
def optimize_endpoint(input_data: OptimizeInput):
    """Calculates optimal stint strategy via Dynamic Programming backward induction."""
    try:
        track = get_track(input_data.track_id)
    except KeyError:
        raise CircuitNotFoundError(input_data.track_id)

    result = optimize_strategy(
        track_id=input_data.track_id,
        available_compounds=input_data.available_compounds,
        max_stops=input_data.max_stops,
        risk_aversion=input_data.risk_aversion,
    )

    stints = result["optimal_strategy"]
    mc_strategy = StrategyInput(
        track_id=input_data.track_id,
        compounds=[s["compound"] for s in stints],
        pit_laps=[s["end_lap"] for s in stints[:-1]],
        num_laps=track["num_laps"],
        base_lap_time=track["base_lap_time"],
        pit_stop_time_loss=track["pit_stop_time_loss"],
        sc_probability=track.get("sc_probability", 0.04),
        weather_enabled=input_data.weather_enabled,
        weather_start_state=input_data.weather_start_state,
        num_simulations=5000,
    )
    resolved = resolve_track_params(mc_strategy)
    race_times, _, sc_info = simulate_strategy_vectorized(
        compounds=resolved.get("compounds"),
        pit_laps=resolved.get("pit_laps"),
        num_laps=resolved.get("num_laps"),
        base_lap_time=resolved.get("base_lap_time"),
        pit_stop_time_loss=resolved.get("pit_stop_time_loss"),
        num_simulations=resolved.get("num_simulations", 5000),
        sc_probability=resolved.get("sc_probability", 0.04),
        tire_wear_multiplier=resolved.get("tire_wear_multiplier"),
        pit_loss_variance=resolved.get("pit_loss_variance", 0.0),
        weather_enabled=resolved.get("weather_enabled", False),
        weather_start_state=resolved.get("weather_start_state", "dry"),
        driver_pace_offset=resolved.get("driver_pace_offset", 0.0),
        driver_consistency=resolved.get("driver_consistency", 0.15),
    )
    result["monte_carlo_distribution"] = {
        "race_times": race_times.round(2).tolist(),
        "summary": summarize_simulation(race_times),
        "strategy": mc_strategy,
        "sc_info": sc_info,
    }
    return result


@router.post("/optimize-mcts", response_model=MCTSResponse)
def optimize_mcts_endpoint(input_data: MCTSRequest):
    """Executes Monte Carlo Tree Search to dynamically replan mid-race decisions under uncertainty."""
    try:
        track = get_track(input_data.track_id)
    except KeyError:
        raise CircuitNotFoundError(input_data.track_id)

    driver = get_driver(input_data.driver_id)

    num_laps = track.get("num_laps", 57)
    base_lap_time = track.get("base_lap_time", 94.0)
    pit_stop_loss = track.get("pit_stop_time_loss", 22.0)

    start_lap = input_data.current_lap or 1
    overrides = input_data.current_state_overrides or {}

    state = MCTSState(
        lap=start_lap,
        compound=overrides.get("compound", "medium"),
        tire_age=overrides.get("tire_age", 1),
        weather_state=overrides.get("weather_state", input_data.weather_start_state),
        is_sc_active=overrides.get("is_sc_active", False),
        stops_made=overrides.get("stops_made", 0),
    )

    solver = MCTSSolver(
        track_id=input_data.track_id,
        driver_id=input_data.driver_id,
        num_laps=num_laps,
        base_lap_time=base_lap_time,
        pit_stop_loss=pit_stop_loss,
        available_compounds=input_data.available_compounds,
        max_stops=input_data.max_stops,
        sc_prob=input_data.sc_probability,
        risk_aversion=input_data.risk_aversion,
        weather_enabled=input_data.weather_enabled,
        driver_pace_offset=driver["pace_offset"],
        driver_consistency=driver["consistency"],
        track_evolution_rate=track.get("track_evolution_rate", 0.02),
        use_hybrid_evaluation=input_data.use_hybrid_evaluation,
    )

    solver.search(
        state,
        budget=input_data.search_budget,
        refine_top_k=input_data.refine_top_k,
    )

    best_act = solver.get_best_action()
    dt_data = solver.get_decision_tree_data()

    expected_time = 0.0
    for cand in dt_data["candidates"]:
        if cand["action"] == best_act:
            expected_time = cand["expected_time"]
            break

    if start_lap > 1:
        expected_time += (start_lap - 1) * base_lap_time

    return {
        "policy": solver.generate_policy_rules(),
        "expected_time": expected_time,
        "win_rate_vs_fixed_dp": None,
        "decision_tree": dt_data,
        "diagnostics": solver.get_search_stats(),
    }
