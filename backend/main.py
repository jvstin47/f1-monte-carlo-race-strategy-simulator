from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from typing import Dict, Any

from models import (
    StrategyInput, CompareInput, SimulationResponse, CompareResponse,
    UndercutInput, UndercutResponse, OptimizeInput, OptimizeResponse
)
from simulator import (
    simulate_strategy_vectorized, summarize_simulation, compare_strategies,
    analyze_undercut_curve, DEFAULT_COMPOUNDS
)
from fastf1_calibrator import load_and_calibrate_fastf1
from tracks import TRACKS, get_track
from optimizer import optimize_strategy

app = FastAPI(
    title="F1 Monte Carlo Strategy Simulator API v3",
    description="Vectorized Monte Carlo engine supporting N-stop strategies (1-stop to 4-stop), Safety Cars, Two-Car Undercut modeling, FastF1 real telemetry calibration, Stochastic Weather, and Strategy Optimization.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ],
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
    return data

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "F1 Monte Carlo Strategy Simulator v3",
        "available_compounds": list(DEFAULT_COMPOUNDS.keys())
    }

@app.get("/tracks")
def get_tracks_endpoint():
    return TRACKS

@app.post("/optimize", response_model=OptimizeResponse)
def optimize_endpoint(input_data: OptimizeInput):
    result = optimize_strategy(
        track_id=input_data.track_id,
        available_compounds=input_data.available_compounds,
        max_stops=input_data.max_stops
    )
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
        weather_pit_threshold=resolved_params.get("weather_pit_threshold", 3)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8005, reload=True)
