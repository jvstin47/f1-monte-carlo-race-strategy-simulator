import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from weather import generate_weather_matrix, compute_weather_compound_penalty, WEATHER_COMPOUNDS
from tracks import get_track


DEFAULT_COMPOUNDS = {
    "soft": {
        "wear_rate": 0.14,
        "cliff_threshold": 15,
        "cliff_penalty": 0.03
    },
    "medium": {
        "wear_rate": 0.08,
        "cliff_threshold": 24,
        "cliff_penalty": 0.02
    },
    "hard": {
        "wear_rate": 0.04,
        "cliff_threshold": 38,
        "cliff_penalty": 0.01
    }
}


def calculate_tire_degradation(compound_name: str, tire_age: int, compound_params: Dict[str, Any] = None) -> float:
    params = compound_params or DEFAULT_COMPOUNDS.get(compound_name.lower(), DEFAULT_COMPOUNDS["medium"])
    wear_rate = params.get("wear_rate", 0.08)
    cliff_threshold = params.get("cliff_threshold", 24)
    cliff_penalty = params.get("cliff_penalty", 0.02)

    deg = wear_rate * tire_age
    if tire_age > cliff_threshold:
        overage = tire_age - cliff_threshold
        deg += cliff_penalty * (overage ** 2)

    return deg

def generate_safety_car_matrix(
    num_simulations: int,
    num_laps: int,
    sc_probability: float = 0.04,
    sc_duration: int = 5,
    seed: int = None
) -> np.ndarray:
    if seed is not None:
        np.random.seed(seed)

    sc_matrix = np.zeros((num_simulations, num_laps), dtype=bool)
    if sc_probability <= 0:
        return sc_matrix

    triggers = np.random.random((num_simulations, num_laps)) < sc_probability

    for sim_idx in range(num_simulations):
        sc_laps = np.where(triggers[sim_idx])[0]
        valid_laps = [l for l in sc_laps if 2 <= l < num_laps - 3]
        if valid_laps:
            start_lap = valid_laps[0]
            end_lap = min(start_lap + sc_duration, num_laps)
            sc_matrix[sim_idx, start_lap:end_lap] = True

    return sc_matrix

def parse_strategy_stints(
    compound_1: Optional[str] = None,
    compound_2: Optional[str] = None,
    pit_lap: Optional[int] = None,
    compounds: Optional[List[str]] = None,
    pit_laps: Optional[List[int]] = None
) -> Tuple[List[str], List[int]]:
    if compounds and len(compounds) > 0:
        comp_list = [c.lower() for c in compounds]
        laps_list = sorted(pit_laps) if pit_laps else []
        while len(comp_list) < len(laps_list) + 1:
            comp_list.append("medium")
        return comp_list, laps_list

    c1 = compound_1.lower() if compound_1 else "soft"
    c2 = compound_2.lower() if compound_2 else "medium"
    pl = pit_lap if pit_lap is not None else 18
    return [c1, c2], [pl]

def simulate_strategy_vectorized(
    compound_1: str = "soft",
    compound_2: str = "medium",
    pit_lap: int = 18,
    compounds: Optional[List[str]] = None,
    pit_laps: Optional[List[int]] = None,
    num_laps: int = 57,
    base_lap_time: float = 94.0,
    pit_stop_time_loss: float = 22.0,
    num_simulations: int = 10000,
    random_std: float = 0.15,
    sc_probability: float = 0.0,
    sc_pit_loss: float = 8.0,
    is_reactive_sc: bool = False,
    reactive_window: int = 8,
    enable_fuel_model: bool = True,
    fuel_effect_per_lap: float = 0.033, # ~1.8kg/lap burn at 0.035s/kg = ~0.033s/lap speedup
    compound_params: Dict[str, Any] = None,
    tire_wear_multiplier: Dict[str, float] = None,
    pit_loss_variance: float = 0.0,
    weather_enabled: bool = False,
    weather_start_state: str = "dry",
    weather_pit_threshold: int = 3,
    driver_pace_offset: float = 0.0,
    driver_consistency: float = 0.15,
    enable_track_evolution: bool = True,
    track_evolution_rate: float = 0.02,
    enable_traffic_loss: bool = True,
    seed: int = None
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Simulates an N-stop race strategy (1-stop, 2-stop, 3-stop, 4-stop, etc.) over num_simulations runs.
    Includes fuel weight burn-off model and stochastic Safety Car events.
    """
    if seed is not None:
        np.random.seed(seed)

    comp_list, planned_pit_laps = parse_strategy_stints(
        compound_1=compound_1, compound_2=compound_2, pit_lap=pit_lap,
        compounds=compounds, pit_laps=pit_laps
    )

    random_variations = np.random.normal(0, driver_consistency, size=(num_simulations, num_laps))
    
    lap_indices = np.arange(1, num_laps + 1)
    if enable_track_evolution:
        track_evolution_penalties = -track_evolution_rate * np.log1p(lap_indices)
    else:
        track_evolution_penalties = np.zeros(num_laps)
        
    # Backmarker Traffic Loss: Simulates probabilistic time lost when catching and passing lapped cars.
    # Note: This is distinct from the Two-Car Undercut 'dirty_air_penalty', which is a deterministic penalty 
    # applied only when directly tailing the specific rival car being modeled.
    if enable_traffic_loss:
        traffic_prob_matrix = np.random.random((num_simulations, num_laps))
        backmarker_traffic_loss_matrix = np.where(traffic_prob_matrix < 0.05, np.random.uniform(0.1, 0.4, size=(num_simulations, num_laps)), 0.0)
    else:
        backmarker_traffic_loss_matrix = np.zeros((num_simulations, num_laps))
        
    sc_matrix = generate_safety_car_matrix(num_simulations, num_laps, sc_probability=sc_probability, seed=seed)
    sc_occurrence_count = int(np.sum(np.any(sc_matrix, axis=1)))

    if weather_enabled:
        weather_matrix = generate_weather_matrix(num_simulations, num_laps, start_state=weather_start_state, seed=seed)
    else:
        weather_matrix = np.zeros((num_simulations, num_laps), dtype=np.int8)

    lap_time_matrix = np.zeros((num_simulations, num_laps))
    sc_pace_lap_time = base_lap_time * 1.35

    pit_loss_noise = np.random.normal(0, pit_loss_variance, size=(num_simulations, num_laps)) if pit_loss_variance > 0 else np.zeros((num_simulations, num_laps))

    for sim_idx in range(num_simulations):
        sim_sc = sc_matrix[sim_idx]
        sim_weather = weather_matrix[sim_idx]
        actual_pit_laps = list(planned_pit_laps)
        sim_comp_list = list(comp_list)

        if is_reactive_sc and len(actual_pit_laps) > 0:
            for k_idx, target_pl in enumerate(actual_pit_laps):
                min_r_lap = max(2, target_pl - reactive_window)
                sc_laps_in_win = np.where(sim_sc[min_r_lap-1:target_pl])[0]
                if len(sc_laps_in_win) > 0:
                    actual_pit_laps[k_idx] = min_r_lap + sc_laps_in_win[0]
                    break

        wet_damp_streak = 0
        weather_pit_triggered = False

        for lap_idx in range(1, num_laps + 1):
            is_sc_lap = sim_sc[lap_idx - 1]
            weather_state = sim_weather[lap_idx - 1]
            
            # Weather logic
            if weather_enabled:
                if weather_state in [1, 2]: # damp or wet
                    wet_damp_streak += 1
                else:
                    wet_damp_streak = 0

                stint_idx_for_check = sum([1 for pl in actual_pit_laps if lap_idx > pl])
                current_compound_check = sim_comp_list[min(stint_idx_for_check, len(sim_comp_list) - 1)]

                if wet_damp_streak >= weather_pit_threshold and current_compound_check in ["soft", "medium", "hard"]:
                    # Trigger reactive pit for intermediates
                    if lap_idx not in actual_pit_laps:
                        actual_pit_laps.append(lap_idx)
                        actual_pit_laps.sort()
                        # Replace subsequent compounds with intermediate
                        idx_to_replace = actual_pit_laps.index(lap_idx)
                        sim_comp_list.insert(idx_to_replace + 1, "intermediate")
                        wet_damp_streak = 0
                        weather_pit_triggered = True

            stint_idx = 0
            stint_start_lap = 1
            for p_idx, pl in enumerate(actual_pit_laps):
                if lap_idx > pl:
                    stint_idx = p_idx + 1
                    stint_start_lap = pl + 1
                else:
                    break

            compound = sim_comp_list[min(stint_idx, len(sim_comp_list) - 1)]
            tire_age = lap_idx - stint_start_lap + 1

            is_pit_lap = lap_idx in actual_pit_laps
            pit_loss = (sc_pit_loss if is_sc_lap else pit_stop_time_loss) if is_pit_lap else 0.0
            if is_pit_lap and pit_loss_variance > 0:
                pit_loss += pit_loss_noise[sim_idx, lap_idx - 1]

            fuel_penalty = (fuel_effect_per_lap * (num_laps - lap_idx)) if enable_fuel_model else 0.0

            if is_sc_lap:
                lap_time = sc_pace_lap_time + pit_loss + random_variations[sim_idx, lap_idx - 1] * 0.2
            else:
                params = compound_params.copy() if compound_params else DEFAULT_COMPOUNDS.get(compound, DEFAULT_COMPOUNDS["medium"]).copy()
                if tire_wear_multiplier:
                    mult = tire_wear_multiplier.get(compound, 1.0)
                    params["wear_rate"] = params.get("wear_rate", 0.08) * mult
                    
                deg = calculate_tire_degradation(compound, tire_age, params)
                weather_penalty = compute_weather_compound_penalty(compound, weather_state) if weather_enabled else 1.0
                
                track_evol = track_evolution_penalties[lap_idx - 1]
                t_loss = backmarker_traffic_loss_matrix[sim_idx, lap_idx - 1]
                
                lap_time = (base_lap_time * weather_penalty) + deg + fuel_penalty + pit_loss + random_variations[sim_idx, lap_idx - 1] + driver_pace_offset + track_evol + t_loss

            lap_time_matrix[sim_idx, lap_idx - 1] = lap_time

    total_race_times = np.sum(lap_time_matrix, axis=1)

    sc_info = {
        "sc_probability": sc_probability,
        "sc_races_triggered": sc_occurrence_count,
        "sc_races_pct": round((sc_occurrence_count / num_simulations) * 100, 2),
        "is_reactive_sc": is_reactive_sc,
        "num_stops": len(planned_pit_laps)
    }

    return total_race_times, lap_time_matrix, sc_info

def summarize_simulation(race_times: np.ndarray, num_bins: int = 30) -> Dict[str, Any]:
    mean_val = float(np.mean(race_times))
    median_val = float(np.median(race_times))
    std_val = float(np.std(race_times))
    min_val = float(np.min(race_times))
    max_val = float(np.max(race_times))
    p5_val = float(np.percentile(race_times, 5))
    p95_val = float(np.percentile(race_times, 95))

    counts, bin_edges = np.histogram(race_times, bins=num_bins)
    histogram_data = []
    for i in range(len(counts)):
        bin_center = float((bin_edges[i] + bin_edges[i+1]) / 2.0)
        histogram_data.append({
            "bin_min": float(bin_edges[i]),
            "bin_max": float(bin_edges[i+1]),
            "bin_center": round(bin_center, 2),
            "count": int(counts[i])
        })

    return {
        "mean": round(mean_val, 2),
        "median": round(median_val, 2),
        "std_dev": round(std_val, 2),
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "p5": round(p5_val, 2),
        "p95": round(p95_val, 2),
        "histogram": histogram_data
    }

def compare_strategies(
    strategy_a: Dict[str, Any],
    strategy_b: Dict[str, Any],
    num_simulations: int = 10000,
    compound_params: Dict[str, Any] = None,
    tire_wear_multiplier: Dict[str, float] = None,
    pit_loss_variance: float = 0.0,
    weather_enabled: bool = False,
    weather_start_state: str = "dry",
    weather_pit_threshold: int = 3,
    seed: int = 42
) -> Dict[str, Any]:
    times_a, _, sc_info_a = simulate_strategy_vectorized(
        compound_1=strategy_a.get("compound_1", "soft"),
        compound_2=strategy_a.get("compound_2", "medium"),
        pit_lap=strategy_a.get("pit_lap", 18),
        compounds=strategy_a.get("compounds"),
        pit_laps=strategy_a.get("pit_laps"),
        num_laps=strategy_a.get("num_laps", 57),
        base_lap_time=strategy_a.get("base_lap_time", 94.0),
        pit_stop_time_loss=strategy_a.get("pit_stop_time_loss", 22.0),
        num_simulations=num_simulations,
        random_std=strategy_a.get("random_std", 0.15),
        sc_probability=strategy_a.get("sc_probability", 0.0),
        is_reactive_sc=strategy_a.get("is_reactive_sc", False),
        reactive_window=strategy_a.get("reactive_window", 8),
        enable_fuel_model=strategy_a.get("enable_fuel_model", True),
        compound_params=strategy_a.get("compound_params"),
        tire_wear_multiplier=strategy_a.get("tire_wear_multiplier"),
        pit_loss_variance=strategy_a.get("pit_loss_variance", 0.0),
        weather_enabled=strategy_a.get("weather_enabled", False),
        weather_start_state=strategy_a.get("weather_start_state", "dry"),
        weather_pit_threshold=strategy_a.get("weather_pit_threshold", 3),
        driver_pace_offset=strategy_a.get("driver_pace_offset", 0.0),
        driver_consistency=strategy_a.get("driver_consistency", strategy_a.get("random_std", 0.15)),
        enable_track_evolution=strategy_a.get("enable_track_evolution", True),
        track_evolution_rate=strategy_a.get("track_evolution_rate", 0.02),
        enable_traffic_loss=strategy_a.get("enable_traffic_loss", True),
        seed=seed
    )

    times_b, _, sc_info_b = simulate_strategy_vectorized(
        compound_1=strategy_b.get("compound_1", "soft"),
        compound_2=strategy_b.get("compound_2", "medium"),
        pit_lap=strategy_b.get("pit_lap", 18),
        compounds=strategy_b.get("compounds"),
        pit_laps=strategy_b.get("pit_laps"),
        num_laps=strategy_b.get("num_laps", 57),
        base_lap_time=strategy_b.get("base_lap_time", 94.0),
        pit_stop_time_loss=strategy_b.get("pit_stop_time_loss", 22.0),
        num_simulations=num_simulations,
        sc_probability=strategy_b.get("sc_probability", 0.0),
        is_reactive_sc=strategy_b.get("is_reactive_sc", False),
        reactive_window=strategy_b.get("reactive_window", 8),
        enable_fuel_model=strategy_b.get("enable_fuel_model", True),
        compound_params=strategy_b.get("compound_params"),
        tire_wear_multiplier=strategy_b.get("tire_wear_multiplier"),
        pit_loss_variance=strategy_b.get("pit_loss_variance", 0.0),
        weather_enabled=strategy_b.get("weather_enabled", False),
        weather_start_state=strategy_b.get("weather_start_state", "dry"),
        weather_pit_threshold=strategy_b.get("weather_pit_threshold", 3),
        driver_pace_offset=strategy_b.get("driver_pace_offset", 0.0),
        driver_consistency=strategy_b.get("driver_consistency", strategy_b.get("random_std", 0.15)),
        enable_track_evolution=strategy_b.get("enable_track_evolution", True),
        track_evolution_rate=strategy_b.get("track_evolution_rate", 0.02),
        enable_traffic_loss=strategy_b.get("enable_traffic_loss", True),
        seed=seed
    )

    summary_a = summarize_simulation(times_a)
    summary_b = summarize_simulation(times_b)

    wins_a = int(np.sum(times_a < times_b))
    wins_b = int(np.sum(times_b < times_a))

    win_prob_a = round(float(wins_a / num_simulations) * 100, 2)
    win_prob_b = round(float(wins_b / num_simulations) * 100, 2)

    min_time = min(np.min(times_a), np.min(times_b))
    max_time = max(np.max(times_a), np.max(times_b))
    bins = np.linspace(min_time, max_time, 35)

    counts_a, _ = np.histogram(times_a, bins=bins)
    counts_b, _ = np.histogram(times_b, bins=bins)

    combined_histogram = []
    for i in range(len(counts_a)):
        center = round(float((bins[i] + bins[i+1]) / 2.0), 2)
        combined_histogram.append({
            "bin_center": center,
            "count_a": int(counts_a[i]),
            "count_b": int(counts_b[i])
        })

    return {
        "strategy_a_summary": summary_a,
        "strategy_b_summary": summary_b,
        "win_probability_a": win_prob_a,
        "win_probability_b": win_prob_b,
        "combined_histogram": combined_histogram,
        "sc_info_a": sc_info_a,
        "sc_info_b": sc_info_b
    }

def simulate_two_car_undercut(
    car_a_pit_delta: int,
    base_pit_lap_b: int = 20,
    car_a_compound_1: str = "medium",
    car_a_compound_2: str = "hard",
    car_b_compound_1: str = "medium",
    car_b_compound_2: str = "hard",
    num_laps: int = 57,
    base_lap_time: float = 94.0,
    pit_stop_loss: float = 22.0,
    initial_gap_seconds: float = 1.0,
    dirty_air_penalty: float = 0.25,
    enable_fuel_model: bool = True,
    num_simulations: int = 10000,
    random_std: float = 0.15,
    compound_params: Dict[str, Any] = None,
    tire_wear_multiplier: Dict[str, float] = None,
    pit_loss_variance: float = 0.0,
    weather_enabled: bool = False,
    weather_start_state: str = "dry",
    weather_pit_threshold: int = 3,
    seed: int = 42
) -> Dict[str, Any]:
    np.random.seed(seed)
    
    pit_lap_a = max(2, base_pit_lap_b + car_a_pit_delta)
    pit_lap_b = base_pit_lap_b

    noise_a = np.random.normal(0, random_std, size=(num_simulations, num_laps))
    noise_b = np.random.normal(0, random_std, size=(num_simulations, num_laps))

    cum_time_a = np.zeros(num_simulations) + initial_gap_seconds
    cum_time_b = np.zeros(num_simulations)

    for lap_idx in range(1, num_laps + 1):
        if lap_idx <= pit_lap_a:
            c_a = car_a_compound_1
            age_a = lap_idx
            pit_a = pit_stop_loss if lap_idx == pit_lap_a else 0.0
        else:
            c_a = car_a_compound_2
            age_a = lap_idx - pit_lap_a
            pit_a = 0.0

        if lap_idx <= pit_lap_b:
            c_b = car_b_compound_1
            age_b = lap_idx
            pit_b = pit_stop_loss if lap_idx == pit_lap_b else 0.0
        else:
            c_b = car_b_compound_2
            age_b = lap_idx - pit_lap_b
            pit_b = 0.0

        deg_a = calculate_tire_degradation(c_a, age_a)
        deg_b = calculate_tire_degradation(c_b, age_b)

        fuel_penalty = (0.033 * (num_laps - lap_idx)) if enable_fuel_model else 0.0

        lap_t_a = base_lap_time + deg_a + fuel_penalty + pit_a + noise_a[:, lap_idx - 1]
        lap_t_b = base_lap_time + deg_b + fuel_penalty + pit_b + noise_b[:, lap_idx - 1]

        gap_a_behind_b = cum_time_a - cum_time_b
        in_dirty_air = (gap_a_behind_b > 0) & (gap_a_behind_b <= 1.5)
        lap_t_a += np.where(in_dirty_air, dirty_air_penalty, 0.0)

        gap_b_behind_a = cum_time_b - cum_time_a
        b_in_dirty_air = (gap_b_behind_a > 0) & (gap_b_behind_a <= 1.5)
        lap_t_b += np.where(b_in_dirty_air, dirty_air_penalty, 0.0)

        cum_time_a += lap_t_a
        cum_time_b += lap_t_b

    undercut_wins = np.sum(cum_time_a < cum_time_b)
    undercut_win_pct = round(float(undercut_wins / num_simulations) * 100, 2)
    mean_time_diff = round(float(np.mean(cum_time_b - cum_time_a)), 2)

    return {
        "car_a_pit_delta": car_a_pit_delta,
        "pit_lap_a": pit_lap_a,
        "pit_lap_b": pit_lap_b,
        "undercut_win_pct": undercut_win_pct,
        "mean_gap_seconds": mean_time_diff,
        "num_simulations": num_simulations
    }

def analyze_undercut_curve(
    base_pit_lap_b: int = 22,
    car_a_compound_1: str = "medium",
    car_a_compound_2: str = "hard",
    car_b_compound_1: str = "medium",
    car_b_compound_2: str = "hard",
    initial_gap_seconds: float = 1.0,
    dirty_air_penalty: float = 0.25,
    num_simulations: int = 5000
) -> List[Dict[str, Any]]:
    curve_data = []
    for delta in range(-4, 4):
        res = simulate_two_car_undercut(
            car_a_pit_delta=delta,
            base_pit_lap_b=base_pit_lap_b,
            car_a_compound_1=car_a_compound_1,
            car_a_compound_2=car_a_compound_2,
            car_b_compound_1=car_b_compound_1,
            car_b_compound_2=car_b_compound_2,
            initial_gap_seconds=initial_gap_seconds,
            dirty_air_penalty=dirty_air_penalty,
            num_simulations=num_simulations
        )
        curve_data.append({
            "pit_delta_laps": delta,
            "pit_lap_a": res["pit_lap_a"],
            "undercut_win_pct": res["undercut_win_pct"],
            "mean_gap_seconds": res["mean_gap_seconds"]
        })

    return curve_data
