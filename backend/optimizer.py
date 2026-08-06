from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from simulator import calculate_tire_degradation, DEFAULT_COMPOUNDS, simulate_strategy_vectorized
from tracks import get_track
from weather import WEATHER_COMPOUNDS

def optimize_strategy(
    track_id: str = "bahrain",
    available_compounds: List[str] = None,
    max_stops: int = 2,
    enable_fuel_model: bool = True,
    fuel_effect_per_lap: float = 0.033,
    risk_aversion: float = 0.0,
) -> Dict[str, Any]:
    """
    Deterministic DP via backward induction.
    State: (lap, compound_idx, tire_age, stops_made)
    Action: stay_out | pit_for(new_compound)

    F1 constraint: must use at least 2 different dry compounds.

    risk_aversion (0-1): the DP table itself is fully deterministic (no
    variance concept), so it always finds the pure-expected-time-minimal
    plan *per starting compound*. To make risk_aversion do something real
    rather than just accepting and discarding it, each starting-compound
    candidate is priced with a real Monte Carlo run and the candidates are
    re-ranked by `expected_time + risk_aversion * std_dev`, using the same
    mean+risk*std convention as mcts_optimizer.risk_adjusted_reward. At
    risk_aversion=0 this is identical to the previous pure-expected-time
    ranking.
    """
    if available_compounds is None:
        available_compounds = ["soft", "medium", "hard"]
    
    track = get_track(track_id)
    num_laps = track["num_laps"]
    base_lap_time = track["base_lap_time"]
    pit_stop_time_loss = track["pit_stop_time_loss"]
    tire_wear_mult = track.get("tire_wear_multiplier", {})

    all_compounds = {**DEFAULT_COMPOUNDS, **WEATHER_COMPOUNDS}
    compounds = []
    compound_indices = {}
    for i, c in enumerate(available_compounds):
        c_lower = c.lower()
        compounds.append(c_lower)
        compound_indices[c_lower] = i
    
    num_compounds = len(compounds)
    max_age = num_laps + 1  # tire age can be at most num_laps
    
    def get_lap_time(compound, tire_age, lap):
        """Compute deterministic expected lap time for given state."""
        params = all_compounds.get(compound, DEFAULT_COMPOUNDS["medium"]).copy()
        
        mult = tire_wear_mult.get(compound, 1.0)
        params["wear_rate"] = params["wear_rate"] * mult
        
        deg = calculate_tire_degradation(compound, tire_age, params)
        fuel_penalty = fuel_effect_per_lap * (num_laps - lap) if enable_fuel_model else 0.0
        return base_lap_time + deg + fuel_penalty

    INF = float('inf')
    
    dp = {}
    action = {}

    for c_idx in range(num_compounds):
        for age in range(1, max_age):
            for stops in range(max_stops + 1):
                dp[(num_laps, c_idx, age, stops)] = 0.0
                action[(num_laps, c_idx, age, stops)] = None

    for lap in range(num_laps - 1, 0, -1):  # lap num_laps-1 down to 1
        for c_idx in range(num_compounds):
            compound = compounds[c_idx]
            for age in range(1, min(lap + 1, max_age)):
                for stops in range(max_stops + 1):
                    lt = get_lap_time(compound, age, lap)

                    next_key = (lap + 1, c_idx, age + 1, stops)
                    if next_key in dp:
                        best_val = lt + dp[next_key]
                        best_action = None
                    else:
                        best_val = INF
                        best_action = None

                    if stops < max_stops:
                        for new_c_idx in range(num_compounds):
                            new_compound = compounds[new_c_idx]
                            pit_key = (lap + 1, new_c_idx, 1, stops + 1)
                            if pit_key in dp:
                                pit_val = lt + pit_stop_time_loss + dp[pit_key]
                                if pit_val < best_val:
                                    best_val = pit_val
                                    best_action = new_compound
                    
                    dp[(lap, c_idx, age, stops)] = best_val
                    action[(lap, c_idx, age, stops)] = best_action

    best_start_val = INF
    best_start_compound = 0
    
    results = []
    
    for c_idx in range(num_compounds):
        start_key = (1, c_idx, 1, 0)
        if start_key in dp and dp[start_key] < INF:
            strategy = trace_strategy(action, compounds, c_idx, num_laps, max_stops)
            unique_compounds = set(s["compound"] for s in strategy)
            dry_compounds_used = unique_compounds - {"intermediate", "wet"}
            
            if len(dry_compounds_used) >= 2 or len(unique_compounds - dry_compounds_used) > 0:
                results.append({
                    "stints": strategy,
                    "expected_time": round(dp[start_key], 2),
                    "start_compound": compounds[c_idx],
                })

    if risk_aversion > 0 and results:
        # Price each starting-compound candidate with a real Monte Carlo run so
        # risk_aversion has an actual variance figure to weigh against, instead
        # of being accepted and silently discarded.
        for r in results:
            comp_list = [s["compound"] for s in r["stints"]]
            pit_laps_list = [s["end_lap"] for s in r["stints"][:-1]]
            times, _, _ = simulate_strategy_vectorized(
                compounds=comp_list,
                pit_laps=pit_laps_list,
                num_laps=num_laps,
                base_lap_time=base_lap_time,
                pit_stop_time_loss=pit_stop_time_loss,
                num_simulations=2000,
                sc_probability=track.get("sc_probability", 0.04),
                tire_wear_multiplier=tire_wear_mult,
                enable_fuel_model=enable_fuel_model,
                fuel_effect_per_lap=fuel_effect_per_lap,
                seed=42,
            )
            r["std_dev"] = round(float(np.std(times)), 2)
            r["risk_score"] = round(r["expected_time"] + risk_aversion * r["std_dev"], 2)
        results.sort(key=lambda x: x["risk_score"])
    else:
        for r in results:
            r["std_dev"] = None
            r["risk_score"] = r["expected_time"]
        results.sort(key=lambda x: x["expected_time"])

    if not results:
        return {
            "optimal_strategy": [{"compound": "medium", "start_lap": 1, "end_lap": num_laps // 2},
                                  {"compound": "hard", "start_lap": num_laps // 2 + 1, "end_lap": num_laps}],
            "expected_time": 0.0,
            "top_5_alternatives": [],
        }

    optimal = results[0]
    top_5 = results[:5]

    return {
        "optimal_strategy": optimal["stints"],
        "expected_time": optimal["expected_time"],
        "top_5_alternatives": [
            {
                "rank": i + 1,
                "stints": r["stints"],
                "expected_time": r["expected_time"],
                "delta_to_optimal": round(r["expected_time"] - optimal["expected_time"], 2),
                "std_dev": r["std_dev"],
            }
            for i, r in enumerate(top_5)
        ],
    }

def trace_strategy(action_table, compounds, start_c_idx, num_laps, max_stops):
    """Trace forward through the action table to reconstruct strategy stints."""
    stints = []
    current_compound = compounds[start_c_idx]
    current_c_idx = start_c_idx
    stint_start = 1
    age = 1
    stops = 0
    
    for lap in range(1, num_laps + 1):
        key = (lap, current_c_idx, age, stops)
        act = action_table.get(key)
        
        if act is not None and lap < num_laps:
            stints.append({"compound": current_compound, "start_lap": stint_start, "end_lap": lap})
            current_compound = act
            current_c_idx = compounds.index(act)
            stint_start = lap + 1
            age = 1
            stops += 1
        else:
            age += 1

    stints.append({"compound": current_compound, "start_lap": stint_start, "end_lap": num_laps})
    return stints
