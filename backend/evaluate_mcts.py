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
                           mcts_rollout_sims, replan_interval,
                           use_hybrid_evaluation=True, refine_top_k=0,
                           refine_sample_weight=3):
    """Execute the real MCTSSolver as a rolling replanner: re-query it at race
    start, whenever a Safety Car appears, whenever the weather regime changes,
    and periodically every `replan_interval` laps otherwise.

    use_hybrid_evaluation=True runs the v5 hybrid solver (cheap heuristic
    leaves by default, escalating on triggers -- see mcts_optimizer.py);
    False reproduces the original v4 solver (every leaf gets a real Monte
    Carlo rollout), so the two can be benchmarked head-to-head against
    identical race conditions and an identical iteration budget."""
    num_races = weather_matrix.shape[0]
    sc_pace = base_lap_time * 1.35

    times = np.zeros(num_races)
    total_high_fidelity = 0
    total_heuristic = 0
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
                    track_evolution_rate=0.0, rollout_num_simulations=mcts_rollout_sims,
                    use_hybrid_evaluation=use_hybrid_evaluation
                )
                solver.search(state, budget=mcts_budget, refine_top_k=refine_top_k,
                               refine_sample_weight=refine_sample_weight)
                pending_action = solver.get_best_action()
                last_replan_lap = lap
                stats = solver.get_search_stats()
                total_high_fidelity += stats["high_fidelity_rollouts"]
                total_heuristic += stats["heuristic_evaluations"]

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
    return times, {"high_fidelity_rollouts": total_high_fidelity, "heuristic_evaluations": total_heuristic}


def _compare(baseline_label, baseline_times, candidate_label, candidate_times, num_races):
    """Head-to-head summary between a baseline and a candidate over identical
    races. Sign convention matches this project's established one throughout
    (docs/archive/PROJECT_STATUS_v4.md, the original evaluate_mcts.py):
    `time_saved = baseline - candidate`, so POSITIVE means the candidate was
    FASTER (saved time relative to the baseline), negative means the
    candidate was slower."""
    diff = baseline_times - candidate_times  # positive = candidate faster
    baseline_wins = int(np.sum(baseline_times < candidate_times))
    candidate_wins = int(np.sum(candidate_times < baseline_times))
    ties = num_races - baseline_wins - candidate_wins
    return {
        f"{baseline_label}_win_pct": round(baseline_wins / num_races * 100, 1),
        f"{candidate_label}_win_pct": round(candidate_wins / num_races * 100, 1),
        "tie_pct": round(ties / num_races * 100, 1),
        f"mean_time_saved_by_{candidate_label}": round(float(np.mean(diff)), 2),
        f"median_time_saved_by_{candidate_label}": round(float(np.median(diff)), 2),
        f"max_time_saved_by_{candidate_label}": round(float(np.max(diff)), 2),
        f"min_time_saved_by_{candidate_label}": round(float(np.min(diff)), 2),
    }


def evaluate_mcts_vs_dp(num_races=25, track_id="bahrain", seed=42,
                         mcts_budget=60, mcts_rollout_sims=120, replan_interval=6,
                         run_v4_classic=True, refine_top_k=2, refine_sample_weight=3,
                         sc_prob=0.08, weather_start_state="dry", max_stops=2,
                         verbose=True):
    """Three-way empirical comparison, all against identical per-race weather/
    Safety Car/noise realizations: the DP-optimal fixed schedule, the v4
    "classic" MCTS (every leaf gets a real Monte Carlo rollout), and the v5
    hybrid MCTS (cheap heuristic leaves by default, selective escalation --
    see mcts_optimizer.py). Set run_v4_classic=False to skip the v4 arm and
    only benchmark v5 vs. DP (faster).

    sc_prob / weather_start_state / max_stops are exposed (rather than
    hardcoded) so this function can drive the v5 Phase 6 scenario-group
    benchmark suite (benchmark_suite.py) without duplicating this logic."""
    np.random.seed(seed)

    track = get_track(track_id)
    num_laps = track["num_laps"]
    base_lap_time = track["base_lap_time"]
    pit_stop_time_loss = track["pit_stop_time_loss"]
    sc_pit_loss = 8.0
    fuel_effect_per_lap = 0.033

    def _print(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    _print(f"Computing DP-optimal fixed schedule for {track_id}...")
    dp_result = optimize_strategy(track_id, ["soft", "medium", "hard"], max_stops=max_stops)
    dp_stints = dp_result["optimal_strategy"]
    _print(f"DP schedule: {[(s['compound'], s['start_lap'], s['end_lap']) for s in dp_stints]}")

    sc_matrix = generate_safety_car_matrix(num_races, num_laps, sc_probability=sc_prob, seed=seed)
    weather_matrix = generate_weather_matrix(num_races, num_laps, start_state=weather_start_state, seed=seed)
    noise_matrix = np.random.normal(0, 0.15, size=(num_races, num_laps))

    dp_times = simulate_fixed_schedule(
        dp_stints, weather_matrix, sc_matrix, noise_matrix, num_laps,
        base_lap_time, pit_stop_time_loss, sc_pit_loss, fuel_effect_per_lap
    )

    results = {"num_races": num_races, "track_id": track_id}

    if run_v4_classic:
        _print(f"\nRunning v4 classic MCTS (every leaf = real rollout) over {num_races} races "
              f"(budget={mcts_budget}, rollout_sims={mcts_rollout_sims})...")
        t0 = time.time()
        v4_times, v4_diag = simulate_mcts_rolling(
            weather_matrix, sc_matrix, noise_matrix, num_laps, base_lap_time,
            pit_stop_time_loss, sc_pit_loss, fuel_effect_per_lap, track_id=track_id,
            max_stops=max_stops, sc_prob=sc_prob, risk_aversion=0.3,
            mcts_budget=mcts_budget, mcts_rollout_sims=mcts_rollout_sims,
            replan_interval=replan_interval, use_hybrid_evaluation=False
        )
        v4_exec_t = time.time() - t0
        _print(f"  done in {v4_exec_t:.1f}s ({v4_diag['high_fidelity_rollouts']} rollouts, "
              f"{v4_diag['heuristic_evaluations']} heuristic evals)")
        results["v4_classic_vs_dp"] = _compare("dp", dp_times, "v4_classic", v4_times, num_races)
        results["v4_classic_exec_seconds"] = round(v4_exec_t, 1)
        results["v4_classic_diagnostics"] = v4_diag

    _print(f"\nRunning v5 hybrid MCTS (selective escalation + top-{refine_top_k} adaptive "
          f"refinement) over {num_races} races (budget={mcts_budget}, rollout_sims={mcts_rollout_sims})...")
    t0 = time.time()
    v5_times, v5_diag = simulate_mcts_rolling(
        weather_matrix, sc_matrix, noise_matrix, num_laps, base_lap_time,
        pit_stop_time_loss, sc_pit_loss, fuel_effect_per_lap, track_id=track_id,
        max_stops=max_stops, sc_prob=sc_prob, risk_aversion=0.3,
        mcts_budget=mcts_budget, mcts_rollout_sims=mcts_rollout_sims,
        replan_interval=replan_interval, use_hybrid_evaluation=True,
        refine_top_k=refine_top_k, refine_sample_weight=refine_sample_weight
    )
    v5_exec_t = time.time() - t0
    _print(f"  done in {v5_exec_t:.1f}s ({v5_diag['high_fidelity_rollouts']} rollouts, "
          f"{v5_diag['heuristic_evaluations']} heuristic evals)")
    results["v5_hybrid_vs_dp"] = _compare("dp", dp_times, "v5_hybrid", v5_times, num_races)
    results["v5_hybrid_exec_seconds"] = round(v5_exec_t, 1)
    results["v5_hybrid_diagnostics"] = v5_diag

    if run_v4_classic:
        results["v5_hybrid_vs_v4_classic"] = _compare("v4_classic", v4_times, "v5_hybrid", v5_times, num_races)

    _print(f"\n=== Summary ({num_races} races, {track_id}) ===")
    if run_v4_classic:
        c = results["v4_classic_vs_dp"]
        _print(f"v4 classic MCTS vs DP:  MCTS wins {c['v4_classic_win_pct']}%, DP wins {c['dp_win_pct']}%, "
              f"mean time saved by MCTS {c['mean_time_saved_by_v4_classic']}s  [{v4_exec_t:.1f}s wall]")
    h = results["v5_hybrid_vs_dp"]
    _print(f"v5 hybrid MCTS vs DP:   MCTS wins {h['v5_hybrid_win_pct']}%, DP wins {h['dp_win_pct']}%, "
          f"mean time saved by MCTS {h['mean_time_saved_by_v5_hybrid']}s  [{v5_exec_t:.1f}s wall]")
    if run_v4_classic:
        vv = results["v5_hybrid_vs_v4_classic"]
        _print(f"v5 hybrid vs v4 classic: v5 wins {vv['v5_hybrid_win_pct']}%, v4 wins {vv['v4_classic_win_pct']}%, "
              f"mean time saved by v5 {vv['mean_time_saved_by_v5_hybrid']}s")

    return results


if __name__ == "__main__":
    evaluate_mcts_vs_dp(num_races=25)
