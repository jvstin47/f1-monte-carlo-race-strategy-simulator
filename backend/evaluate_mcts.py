"""
Empirical comparison of the rigid DP-optimal strategy against the MCTS rolling
replanner, using the *actual* production code paths for both:

  - The DP schedule comes from optimizer.optimize_strategy() and is executed
    as a fixed compound/pit-lap schedule that cannot react to conditions.
  - The MCTS policy comes from mcts_optimizer.MCTSSolver, re-queried at
    trigger points (race start, a Safety Car appearing, a weather regime
    change) and on a periodic cadence, mirroring how the /optimize-mcts
    endpoint is actually used for rolling re-planning.

Both policies are executed race-by-race, lap-by-lap, against the *same*
per-race Safety Car matrix, weather matrix, and lap-time noise, so that a
"win" reflects a genuine head-to-head under identical stochastic conditions.
Per-lap physics (tire degradation, weather/compound mismatch penalty, fuel
burn) reuse the exact same functions the vectorized simulator uses
(calculate_tire_degradation, compute_weather_compound_penalty) rather than
hardcoded stand-in penalties, so the result reflects the real model.

MCTS search budget and rollout sample count are reduced from the production
defaults (see MCTSSolver's `rollout_num_simulations`) purely so this script
finishes in a reasonable time when re-querying the solver dozens of times
per race across many races. This trades some search quality for runtime,
but still runs the real algorithm, not a substitute.
"""
import time
import numpy as np
from optimizer import optimize_strategy
from mcts_optimizer import MCTSSolver, MCTSState
from simulator import (
    calculate_tire_degradation, generate_safety_car_matrix,
    generate_weather_matrix, DEFAULT_COMPOUNDS
)
from weather import compute_weather_compound_penalty, WEATHER_COMPOUNDS
from tracks import get_track

ALL_COMPOUNDS = {**DEFAULT_COMPOUNDS, **WEATHER_COMPOUNDS}
WEATHER_NAMES = ["dry", "damp", "wet"]


def lap_physics_time(compound, tire_age, lap, num_laps, base_lap_time,
                      weather_idx, is_sc, sc_pace, fuel_effect_per_lap, noise):
    """Same per-lap formula simulate_strategy_vectorized uses (degradation,
    weather/compound penalty, fuel burn), minus track evolution/traffic loss,
    which are strategy-independent and don't affect the relative comparison."""
    if is_sc:
        return sc_pace + noise * 0.2
    params = ALL_COMPOUNDS.get(compound, DEFAULT_COMPOUNDS["medium"])
    deg = calculate_tire_degradation(compound, tire_age, params)
    weather_mult = compute_weather_compound_penalty(compound, weather_idx)
    fuel_penalty = fuel_effect_per_lap * (num_laps - lap)
    return (base_lap_time * weather_mult) + deg + fuel_penalty + noise


def simulate_fixed_schedule(stints, weather_matrix, sc_matrix, noise_matrix,
                             num_laps, base_lap_time, pit_stop_time_loss,
                             sc_pit_loss, fuel_effect_per_lap):
    """Execute the DP's fixed compound/pit-lap schedule race-by-race. It never
    reacts to weather or Safety Cars beyond incidentally benefiting from a
    discounted pit loss if a planned stop happens to land under one."""
    num_races = weather_matrix.shape[0]
    pit_laps = [s["end_lap"] for s in stints[:-1]]
    compounds = [s["compound"] for s in stints]
    sc_pace = base_lap_time * 1.35

    times = np.zeros(num_races)
    for r in range(num_races):
        stop_idx = 0
        compound = compounds[0]
        tire_age = 1
        total = 0.0
        for lap in range(1, num_laps + 1):
            is_sc = bool(sc_matrix[r, lap - 1])
            w_idx = int(weather_matrix[r, lap - 1])
            noise = noise_matrix[r, lap - 1]

            lt = lap_physics_time(compound, tire_age, lap, num_laps, base_lap_time,
                                   w_idx, is_sc, sc_pace, fuel_effect_per_lap, noise)

            if stop_idx < len(pit_laps) and lap == pit_laps[stop_idx]:
                lt += sc_pit_loss if is_sc else pit_stop_time_loss
                compound = compounds[stop_idx + 1]
                tire_age = 1
                stop_idx += 1
            else:
                tire_age += 1

            total += lt
        times[r] = total
    return times


def simulate_mcts_rolling(weather_matrix, sc_matrix, noise_matrix, num_laps,
                           base_lap_time, pit_stop_time_loss, sc_pit_loss,
                           fuel_effect_per_lap, track_id, max_stops, sc_prob,
                           risk_aversion, mcts_budget,
                           mcts_rollout_sims, replan_interval):
    """Execute the real MCTSSolver as a rolling replanner: re-query it at race
    start, whenever a Safety Car appears, whenever the weather regime changes,
    and periodically every `replan_interval` laps otherwise."""
    num_races = weather_matrix.shape[0]
    sc_pace = base_lap_time * 1.35

    times = np.zeros(num_races)
    for r in range(num_races):
        compound = "medium"
        tire_age = 1
        stops = 0
        total = 0.0
        last_weather_idx = int(weather_matrix[r, 0])
        last_is_sc = False
        last_replan_lap = -replan_interval
        pending_action = "stay_out"

        for lap in range(1, num_laps + 1):
            is_sc = bool(sc_matrix[r, lap - 1])
            w_idx = int(weather_matrix[r, lap - 1])
            noise = noise_matrix[r, lap - 1]
            weather_changed = w_idx != last_weather_idx
            sc_just_triggered = is_sc and not last_is_sc
            due_for_replan = (lap - last_replan_lap) >= replan_interval

            # Trigger events fire on the rising edge (SC just appeared / weather just
            # changed), not on every lap the condition remains true -- otherwise a
            # multi-lap SC period re-invokes a fresh, stateless search every single lap
            # with no memory of a decision just made, which can flip-flop pit calls.
            if stops < max_stops and (lap == 1 or sc_just_triggered or weather_changed or due_for_replan):
                state = MCTSState(
                    lap=lap, compound=compound, tire_age=tire_age,
                    weather_state=WEATHER_NAMES[w_idx], is_sc_active=is_sc,
                    stops_made=stops
                )
                # Only offer wet-weather compounds when conditions actually call for
                # them -- otherwise the search wastes most of its budget pricing out
                # intermediates/wets on a bone-dry lap, starving the decisions that
                # actually matter.
                candidate_compounds = (
                    ["soft", "medium", "hard"] if w_idx == 0
                    else ["soft", "medium", "hard", "intermediate", "wet"]
                )
                solver = MCTSSolver(
                    track_id=track_id, driver_id="generic", num_laps=num_laps,
                    base_lap_time=base_lap_time, pit_stop_loss=pit_stop_time_loss,
                    available_compounds=candidate_compounds, max_stops=max_stops,
                    sc_prob=sc_prob, risk_aversion=risk_aversion, weather_enabled=True,
                    driver_pace_offset=0.0, driver_consistency=0.15,
                    track_evolution_rate=0.0, rollout_num_simulations=mcts_rollout_sims
                )
                solver.search(state, budget=mcts_budget)
                pending_action = solver.get_best_action()
                last_replan_lap = lap

            last_weather_idx = w_idx
            last_is_sc = is_sc

            lt = lap_physics_time(compound, tire_age, lap, num_laps, base_lap_time,
                                   w_idx, is_sc, sc_pace, fuel_effect_per_lap, noise)

            if pending_action.startswith("pit_") and stops < max_stops:
                new_compound = pending_action.split("_")[1]
                lt += sc_pit_loss if is_sc else pit_stop_time_loss
                compound = new_compound
                tire_age = 1
                stops += 1
                pending_action = "stay_out"
            else:
                tire_age += 1

            total += lt
        times[r] = total
    return times


def evaluate_mcts_vs_dp(num_races=25, track_id="bahrain", seed=42,
                         mcts_budget=60, mcts_rollout_sims=120, replan_interval=6):
    np.random.seed(seed)

    track = get_track(track_id)
    num_laps = track["num_laps"]
    base_lap_time = track["base_lap_time"]
    pit_stop_time_loss = track["pit_stop_time_loss"]
    sc_prob = 0.08  # elevated vs. track default to stress-test replanning value
    sc_pit_loss = 8.0
    fuel_effect_per_lap = 0.033
    max_stops = 2

    print(f"Computing DP-optimal fixed schedule for {track_id}...")
    dp_result = optimize_strategy(track_id, ["soft", "medium", "hard"], max_stops=max_stops)
    dp_stints = dp_result["optimal_strategy"]
    print(f"DP schedule: {[(s['compound'], s['start_lap'], s['end_lap']) for s in dp_stints]}")

    sc_matrix = generate_safety_car_matrix(num_races, num_laps, sc_probability=sc_prob, seed=seed)
    weather_matrix = generate_weather_matrix(num_races, num_laps, start_state="dry", seed=seed)
    noise_matrix = np.random.normal(0, 0.15, size=(num_races, num_laps))

    dp_times = simulate_fixed_schedule(
        dp_stints, weather_matrix, sc_matrix, noise_matrix, num_laps,
        base_lap_time, pit_stop_time_loss, sc_pit_loss, fuel_effect_per_lap
    )

    print(f"Running MCTS rolling replanner over {num_races} races "
          f"(budget={mcts_budget}, rollout_sims={mcts_rollout_sims})...")
    start_time = time.time()
    mcts_times = simulate_mcts_rolling(
        weather_matrix, sc_matrix, noise_matrix, num_laps, base_lap_time,
        pit_stop_time_loss, sc_pit_loss, fuel_effect_per_lap, track_id=track_id,
        max_stops=max_stops, sc_prob=sc_prob, risk_aversion=0.3,
        mcts_budget=mcts_budget, mcts_rollout_sims=mcts_rollout_sims,
        replan_interval=replan_interval
    )
    exec_t = time.time() - start_time

    time_saved = dp_times - mcts_times
    mcts_wins = int(np.sum(mcts_times < dp_times))
    dp_wins = int(np.sum(dp_times < mcts_times))
    ties = num_races - mcts_wins - dp_wins

    print(f"\n--- Results ({num_races} races, MCTS replanning took {exec_t:.1f}s) ---")
    print(f"MCTS (Rolling Replanner) Wins: {mcts_wins} ({mcts_wins / num_races * 100:.1f}%)")
    print(f"DP (Rigid) Wins:                {dp_wins} ({dp_wins / num_races * 100:.1f}%)")
    print(f"Ties:                           {ties} ({ties / num_races * 100:.1f}%)")

    print(f"\n--- Time Saved by MCTS vs DP (seconds, positive = MCTS faster) ---")
    print(f"Mean:   {np.mean(time_saved):.2f}s")
    print(f"Median: {np.median(time_saved):.2f}s")
    print(f"Max:    {np.max(time_saved):.2f}s")
    print(f"Min:    {np.min(time_saved):.2f}s")

    print(f"\n--- Worst-Case Downside Risk ---")
    print(f"DP worst race:   {np.max(dp_times):.2f}s (vs its own median {np.median(dp_times):.2f}s)")
    print(f"MCTS worst race: {np.max(mcts_times):.2f}s (vs its own median {np.median(mcts_times):.2f}s)")

    return {
        "num_races": num_races,
        "mcts_win_pct": round(mcts_wins / num_races * 100, 1),
        "dp_win_pct": round(dp_wins / num_races * 100, 1),
        "tie_pct": round(ties / num_races * 100, 1),
        "mean_time_saved": round(float(np.mean(time_saved)), 2),
        "median_time_saved": round(float(np.median(time_saved)), 2),
        "dp_worst_case": round(float(np.max(dp_times)), 2),
        "mcts_worst_case": round(float(np.max(mcts_times)), 2),
        "dp_median": round(float(np.median(dp_times)), 2),
        "mcts_median": round(float(np.median(mcts_times)), 2),
    }


if __name__ == "__main__":
    evaluate_mcts_vs_dp(num_races=25)
