"""Monte Carlo simulation, comparison, and undercut routes."""

from fastapi import APIRouter
from ...models.strategy import (
    StrategyInput,
    SimulationResponse,
    CompareInput,
    CompareResponse,
)
from ...models.undercut import UndercutInput, UndercutResponse
from ...engine.simulator import (
    simulate_strategy_vectorized,
    summarize_simulation,
    compare_strategies,
    analyze_undercut_curve,
)
from ..dependencies import resolve_track_params

router = APIRouter(tags=["Simulation"])


@router.post("/simulate", response_model=SimulationResponse)
def simulate_endpoint(input_data: StrategyInput):
    """Runs a Monte Carlo simulation for a single race strategy."""
    resolved_params = resolve_track_params(input_data)

    race_times, _, sc_info = simulate_strategy_vectorized(
        compound_1=resolved_params.get("compound_1"),
        compound_2=resolved_params.get("compound_2"),
        pit_lap=resolved_params.get("pit_lap"),
        compounds=resolved_params.get("compounds"),
        pit_laps=resolved_params.get("pit_laps"),
        num_laps=resolved_params.get("num_laps", 57),
        base_lap_time=resolved_params.get("base_lap_time", 94.0),
        pit_stop_time_loss=resolved_params.get("pit_stop_time_loss", 22.0),
        num_simulations=resolved_params.get("num_simulations", 10000),
        random_std=resolved_params.get("random_std", 0.15),
        sc_probability=resolved_params.get("sc_probability", 0.04),
        is_reactive_sc=resolved_params.get("is_reactive_sc", False),
        reactive_window=resolved_params.get("reactive_window", 8),
        tire_wear_multiplier=resolved_params.get("tire_wear_multiplier"),
        pit_loss_variance=resolved_params.get("pit_loss_variance", 0.0),
        weather_enabled=resolved_params.get("weather_enabled", False),
        weather_start_state=resolved_params.get("weather_start_state", "dry"),
        weather_pit_threshold=resolved_params.get("weather_pit_threshold", 3),
        driver_pace_offset=resolved_params.get("driver_pace_offset", 0.0),
        driver_consistency=resolved_params.get(
            "driver_consistency", resolved_params.get("random_std", 0.15)
        ),
        enable_track_evolution=resolved_params.get("enable_track_evolution", True),
        track_evolution_rate=resolved_params.get("track_evolution_rate", 0.02),
        enable_traffic_loss=resolved_params.get("enable_traffic_loss", True),
    )

    summary = summarize_simulation(race_times)

    return {
        "race_times": race_times.round(2).tolist(),
        "summary": summary,
        "strategy": input_data,
        "sc_info": sc_info,
    }


@router.post("/compare", response_model=CompareResponse)
def compare_endpoint(input_data: CompareInput):
    """Runs paired Monte Carlo simulations to compare Strategy A vs Strategy B head-to-head."""
    strat_a_dict = resolve_track_params(input_data.strategy_a)
    strat_b_dict = resolve_track_params(input_data.strategy_b)

    num_sims = input_data.num_simulations or 10000

    results = compare_strategies(
        strategy_a=strat_a_dict,
        strategy_b=strat_b_dict,
        num_simulations=num_sims,
    )

    return {
        "strategy_a_summary": results["strategy_a_summary"],
        "strategy_b_summary": results["strategy_b_summary"],
        "win_probability_a": results["win_probability_a"],
        "win_probability_b": results["win_probability_b"],
        "combined_histogram": results["combined_histogram"],
        "strategy_a": input_data.strategy_a,
        "strategy_b": input_data.strategy_b,
        "sc_info_a": results.get("sc_info_a"),
        "sc_info_b": results.get("sc_info_b"),
    }


@router.post("/undercut-analysis", response_model=UndercutResponse)
def undercut_analysis_endpoint(input_data: UndercutInput):
    """Analyzes two-car undercut success probability curve across pit delta laps."""
    curve = analyze_undercut_curve(
        base_pit_lap_b=input_data.base_pit_lap_b,
        car_a_compound_1=input_data.car_a_compound_1,
        car_a_compound_2=input_data.car_a_compound_2,
        car_b_compound_1=input_data.car_b_compound_1,
        car_b_compound_2=input_data.car_b_compound_2,
        initial_gap_seconds=input_data.initial_gap_seconds,
        dirty_air_penalty=input_data.dirty_air_penalty,
        num_simulations=input_data.num_simulations,
    )

    return {
        "curve_data": curve,
        "base_pit_lap_b": input_data.base_pit_lap_b,
        "initial_gap_seconds": input_data.initial_gap_seconds,
        "dirty_air_penalty": input_data.dirty_air_penalty,
    }
