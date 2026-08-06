from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import numpy as np
from typing import Dict, Any

from models import (
    StrategyInput, CompareInput, SimulationResponse, CompareResponse,
    UndercutInput, UndercutResponse, OptimizeInput, OptimizeResponse,
    MCTSRequest, MCTSResponse
)
from simulator import (
    simulate_strategy_vectorized, summarize_simulation, compare_strategies,
    analyze_undercut_curve, DEFAULT_COMPOUNDS
)
from fastf1_calibrator import load_and_calibrate_fastf1
from tracks import TRACKS, get_track
from drivers import DRIVER_PROFILES, get_driver
from optimizer import optimize_strategy
from mcts_optimizer import MCTSSolver, MCTSState

app = FastAPI(
    title="F1 Monte Carlo Strategy Simulator API v4",
    description="Vectorized Monte Carlo engine with MCTS optimizer, driver profiles, realism layer (fuel/track evolution/traffic), N-stop strategies, Safety Cars, Undercut modeling, FastF1 calibration, Stochastic Weather, and Strategy Optimization.",
    version="4.0.0"
)

_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
_allowed_origins = [o.strip() for o in _origins_env.split(",")] if _origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def resolve_track_params(input_data: StrategyInput) -> Dict[str, Any]:
    data = input_data.dict()
    if input_data.track_id:
        try:
            track = get_track(input_data.track_id)
            data["num_laps"] = track["num_laps"]
            data["base_lap_time"] = track["base_lap_time"]
            data["pit_stop_time_loss"] = track["pit_stop_time_loss"]
            data["sc_probability"] = track.get("sc_probability", data.get("sc_probability", 0.04))
            data["tire_wear_multiplier"] = track.get("tire_wear_multiplier", {})
            data["pit_loss_variance"] = track.get("pit_loss_variance", 0.0)
        except KeyError:
            pass
            
    if data.get("driver_id") and data["driver_id"].lower() != "generic":
        driver = get_driver(data["driver_id"])
        data["driver_pace_offset"] = driver["pace_offset"]
        data["driver_consistency"] = driver["consistency"]
    else:
        # No named driver selected: let random_std drive lap-time variance directly
        # instead of always falling back to the generic profile's fixed consistency.
        data["driver_pace_offset"] = 0.0
        data["driver_consistency"] = data.get("random_std", 0.15)

    return data

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "F1 Monte Carlo Strategy Simulator v4",
        "available_compounds": list(DEFAULT_COMPOUNDS.keys())
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/tracks")
def get_tracks_endpoint():
    return TRACKS

@app.get("/drivers")
def get_drivers_endpoint():
    return DRIVER_PROFILES

@app.post("/optimize", response_model=OptimizeResponse)
def optimize_endpoint(input_data: OptimizeInput):
    result = optimize_strategy(
        track_id=input_data.track_id,
        available_compounds=input_data.available_compounds,
        max_stops=input_data.max_stops,
        risk_aversion=input_data.risk_aversion
    )

    track = get_track(input_data.track_id)
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

@app.post("/simulate", response_model=SimulationResponse)
def simulate_endpoint(input_data: StrategyInput):
    """
    Runs a Monte Carlo simulation for a strategy.
    """
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
        driver_consistency=resolved_params.get("driver_consistency", resolved_params.get("random_std", 0.15)),
        enable_track_evolution=resolved_params.get("enable_track_evolution", True),
        track_evolution_rate=resolved_params.get("track_evolution_rate", 0.02),
        enable_traffic_loss=resolved_params.get("enable_traffic_loss", True)
    )

    summary = summarize_simulation(race_times)

    return {
        "race_times": race_times.round(2).tolist(),
        "summary": summary,
        "strategy": input_data,
        "sc_info": sc_info
    }

@app.post("/compare", response_model=CompareResponse)
def compare_endpoint(input_data: CompareInput):
    """
    Runs paired Monte Carlo simulations to compare Strategy A vs Strategy B head-to-head.
    """
    strat_a_dict = resolve_track_params(input_data.strategy_a)
    strat_b_dict = resolve_track_params(input_data.strategy_b)

    num_sims = input_data.num_simulations or 10000

    results = compare_strategies(
        strategy_a=strat_a_dict,
        strategy_b=strat_b_dict,
        num_simulations=num_sims
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
        "sc_info_b": results.get("sc_info_b")
    }

@app.post("/undercut-analysis", response_model=UndercutResponse)
def undercut_analysis_endpoint(input_data: UndercutInput):
    curve = analyze_undercut_curve(
        base_pit_lap_b=input_data.base_pit_lap_b,
        car_a_compound_1=input_data.car_a_compound_1,
        car_a_compound_2=input_data.car_a_compound_2,
        car_b_compound_1=input_data.car_b_compound_1,
        car_b_compound_2=input_data.car_b_compound_2,
        initial_gap_seconds=input_data.initial_gap_seconds,
        dirty_air_penalty=input_data.dirty_air_penalty,
        num_simulations=input_data.num_simulations
    )

    return {
        "curve_data": curve,
        "base_pit_lap_b": input_data.base_pit_lap_b,
        "initial_gap_seconds": input_data.initial_gap_seconds,
        "dirty_air_penalty": input_data.dirty_air_penalty
    }

@app.get("/fastf1/calibrate")
def fastf1_calibrate_endpoint(year: int = 2023, grand_prix: str = "Bahrain", session_type: str = "R"):
    calibration = load_and_calibrate_fastf1(year=year, grand_prix=grand_prix, session_type=session_type)
    return calibration



@app.post("/optimize-mcts", response_model=MCTSResponse)
def optimize_mcts_endpoint(input_data: MCTSRequest):
    try:
        track = get_track(input_data.track_id)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown track_id: {input_data.track_id}")
    driver = get_driver(input_data.driver_id)
    
    # Base configuration
    num_laps = track.get("num_laps", 57)
    base_lap_time = track.get("base_lap_time", 94.0)
    pit_stop_loss = track.get("pit_stop_time_loss", 22.0)
    
    # Establish starting state for the MCTS
    start_lap = input_data.current_lap or 1
    overrides = input_data.current_state_overrides or {}
    
    state = MCTSState(
        lap=start_lap,
        compound=overrides.get("compound", "medium"),
        tire_age=overrides.get("tire_age", 1),
        weather_state=overrides.get("weather_state", input_data.weather_start_state),
        is_sc_active=overrides.get("is_sc_active", False),
        stops_made=overrides.get("stops_made", 0)
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
        track_evolution_rate=track.get("track_evolution_rate", 0.02)
    )
    
    solver.search(state, budget=1000)
    
    best_act = solver.get_best_action()
    dt_data = solver.get_decision_tree_data()
    
    # Calculate a rough expected time from the best action node
    expected_time = 0.0
    for cand in dt_data["candidates"]:
        if cand["action"] == best_act:
            expected_time = cand["expected_time"]
            break
            
    # Add time already elapsed if replanning from mid-race (simplified approximation)
    if start_lap > 1:
        expected_time += (start_lap - 1) * base_lap_time
        
    return {
        "policy": solver.generate_policy_rules(),
        "expected_time": expected_time,
        "win_rate_vs_fixed_dp": None, # Could compute via a side-by-side run here, but skipping for speed
        "decision_tree": dt_data
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8005))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
