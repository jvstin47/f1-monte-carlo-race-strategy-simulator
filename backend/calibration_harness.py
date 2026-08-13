"""
v5 Phase 1: Heuristic-vs-simulator calibration harness.

Compares the MCTS tree-traversal heuristic (mcts_optimizer.MCTSSolver._simulate's
transition-cost formula -- a flat, compound-agnostic `tire_age * 0.10` degradation
term) against real, simulator-grounded action costs, across a diverse sample of
race states. This is the "quantitative evidence" deliverable for v5 Phase 1
(docs/V5_DESIGN.md, section 19): does the cheap heuristic MCTS actually uses while
descending the tree correctly rank candidate actions relative to what the
production Monte Carlo engine (the real tire-degradation curve + a full rollout)
says?

No MCTS algorithm changes happen here -- this is instrumentation only.

Usage:
    ./venv/bin/python calibration_harness.py
"""
import random
from typing import Any, Dict, List

import numpy as np

from mcts_optimizer import MCTSSolver, MCTSState, get_legal_actions
from simulator import calculate_tire_degradation
from tracks import get_track


def heuristic_action_cost(state: MCTSState, action: str, num_laps: int,
                           base_lap_time: float, pit_stop_loss: float) -> float:
    """Total remaining-race cost the current MCTS traversal heuristic implies for
    `action`, extrapolated across the rest of the race using the SAME flat,
    compound-agnostic formula _simulate() uses for a single edge. This mirrors
    what an un-expanded subtree "looks like" to the search under the heuristic's
    assumptions."""
    if action == "stay_out":
        next_age = state.tire_age + 1
        pit_loss = 0.0
    else:
        next_age = 1
        pit_loss = 8.0 if state.is_sc_active else pit_stop_loss

    this_lap_cost = base_lap_time + (state.tire_age * 0.10) + pit_loss

    remaining = num_laps - state.lap
    future = 0.0
    age = next_age
    for _ in range(remaining):
        future += base_lap_time + age * 0.10
        age += 1

    return this_lap_cost + future


def real_action_cost(solver: MCTSSolver, state: MCTSState, action: str) -> float:
    """Simulator-grounded total remaining-race cost for `action`: this lap's cost
    via the real per-compound degradation curve, plus the production rollout's
    estimate for everything after -- the same two pieces the (sign-fixed)
    _simulate() reward combines, just computed with real physics instead of the
    flat heuristic."""
    if action == "stay_out":
        next_compound = state.compound
        next_age = state.tire_age + 1
        next_stops = state.stops_made
        pit_loss = 0.0
    else:
        next_compound = action.split("_")[1]
        next_age = 1
        next_stops = state.stops_made + 1
        pit_loss = 8.0 if state.is_sc_active else solver.pit_stop_loss

    deg = calculate_tire_degradation(state.compound, state.tire_age)
    this_lap_cost = solver.base_lap_time + deg + pit_loss

    next_state = MCTSState(state.lap + 1, next_compound, next_age, state.weather_state, False, next_stops)
    future_cost = -solver.rollout_eval(next_state)  # rollout_eval returns a negative reward (-cost)

    return this_lap_cost + future_cost


def rank_correlation(a: List[float], b: List[float]) -> float:
    """Spearman rank correlation with proper tied-rank averaging, implemented
    directly (no scipy dependency). Ties matter here: the heuristic frequently
    assigns identical cost to different pit compounds (that's the Phase 1
    finding), so naive positional ranking would silently misrepresent them."""
    n = len(a)
    if n < 2:
        return float("nan")

    def ranks(xs: List[float]) -> List[float]:
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(xs):
            j = i
            while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg_rank = (i + j) / 2.0
            for k in range(i, j + 1):
                r[order[k]] = avg_rank
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    mean_ra, mean_rb = sum(ra) / n, sum(rb) / n
    cov = sum((ra[i] - mean_ra) * (rb[i] - mean_rb) for i in range(n))
    var_a = sum((x - mean_ra) ** 2 for x in ra)
    var_b = sum((x - mean_rb) ** 2 for x in rb)
    if var_a == 0 or var_b == 0:
        return float("nan")
    return cov / (var_a ** 0.5 * var_b ** 0.5)


def sample_states(num_laps: int, compounds: List[str], n: int, seed: int) -> List[MCTSState]:
    """Deliberately spans fresh/mid-stint/past-cliff tire ages, all compounds,
    all weather states, and a mix of Safety Car / stops-made conditions."""
    rng = random.Random(seed)
    states = []
    for _ in range(n):
        lap = rng.randint(1, num_laps - 3)
        compound = rng.choice(compounds)
        tire_age = min(rng.choice([1, 2, 5, 10, 15, 20, 25, 30, 35, 40]), lap)
        weather = rng.choice(["dry", "damp", "wet"])
        is_sc = rng.random() < 0.15
        stops_made = rng.choice([0, 1])
        states.append(MCTSState(lap, compound, max(tire_age, 1), weather, is_sc, stops_made))
    return states


def run_calibration(track_id: str = "bahrain", num_states: int = 60,
                     available_compounds: List[str] = None, max_stops: int = 2,
                     seed: int = 42) -> Dict[str, Any]:
    if available_compounds is None:
        available_compounds = ["soft", "medium", "hard"]

    np.random.seed(seed)

    track = get_track(track_id)
    num_laps = track["num_laps"]
    base_lap_time = track["base_lap_time"]
    pit_stop_loss = track["pit_stop_time_loss"]

    solver = MCTSSolver(
        track_id=track_id, driver_id="generic", num_laps=num_laps,
        base_lap_time=base_lap_time, pit_stop_loss=pit_stop_loss,
        available_compounds=available_compounds, max_stops=max_stops,
        sc_prob=track.get("sc_probability", 0.04), risk_aversion=0.0,
        weather_enabled=True, driver_pace_offset=0.0, driver_consistency=0.15,
        track_evolution_rate=track.get("track_evolution_rate", 0.02),
        rollout_num_simulations=300,
    )

    states = sample_states(num_laps, available_compounds, num_states, seed)

    per_state_results = []
    all_signed_errors = []  # real - heuristic, signed, per (state, action)
    by_compound_errors: Dict[str, List[float]] = {c: [] for c in available_compounds}

    for state in states:
        actions = get_legal_actions(state, max_stops, available_compounds, num_laps)
        if len(actions) < 2:
            continue  # nothing to rank

        heuristic_costs = [heuristic_action_cost(state, a, num_laps, base_lap_time, pit_stop_loss) for a in actions]
        real_costs = [real_action_cost(solver, state, a) for a in actions]

        for a, h, r in zip(actions, heuristic_costs, real_costs):
            err = r - h
            all_signed_errors.append(err)
            target_compound = state.compound if a == "stay_out" else a.split("_")[1]
            by_compound_errors.setdefault(target_compound, []).append(err)

        corr = rank_correlation(heuristic_costs, real_costs)
        heuristic_best = actions[int(np.argmin(heuristic_costs))]
        real_best = actions[int(np.argmin(real_costs))]

        per_state_results.append({
            "state": str(state),
            "actions": actions,
            "heuristic_costs": [round(c, 2) for c in heuristic_costs],
            "real_costs": [round(c, 2) for c in real_costs],
            "rank_correlation": None if np.isnan(corr) else round(corr, 3),
            "heuristic_best": heuristic_best,
            "real_best": real_best,
            "top1_agree": heuristic_best == real_best,
        })

    valid_corrs = [r["rank_correlation"] for r in per_state_results if r["rank_correlation"] is not None]
    top1_agreements = [r["top1_agree"] for r in per_state_results]

    summary = {
        "track_id": track_id,
        "num_states_sampled": len(states),
        "num_states_evaluated": len(per_state_results),
        "mean_rank_correlation": round(float(np.mean(valid_corrs)), 3) if valid_corrs else None,
        "median_rank_correlation": round(float(np.median(valid_corrs)), 3) if valid_corrs else None,
        "top1_agreement_rate_pct": round(100.0 * sum(top1_agreements) / len(top1_agreements), 1) if top1_agreements else None,
        "mean_signed_error_real_minus_heuristic": round(float(np.mean(all_signed_errors)), 2) if all_signed_errors else None,
        "mean_abs_error": round(float(np.mean(np.abs(all_signed_errors))), 2) if all_signed_errors else None,
        "signed_error_by_target_compound": {
            c: {
                "n": len(errs),
                "mean_signed_error": round(float(np.mean(errs)), 2) if errs else None,
            }
            for c, errs in by_compound_errors.items()
        },
    }

    return {"summary": summary, "per_state": per_state_results}


def print_report(results: Dict[str, Any]) -> None:
    s = results["summary"]
    print(f"\n=== v5 Phase 1 Calibration Report ({s['track_id']}) ===")
    print(f"States sampled: {s['num_states_sampled']}  (evaluated: {s['num_states_evaluated']})")
    print(f"Mean rank correlation (heuristic vs. real):  {s['mean_rank_correlation']}")
    print(f"Median rank correlation:                     {s['median_rank_correlation']}")
    print(f"Top-1 agreement rate:                        {s['top1_agreement_rate_pct']}%")
    print(f"Mean signed error (real - heuristic):         {s['mean_signed_error_real_minus_heuristic']}s")
    print(f"Mean absolute error:                          {s['mean_abs_error']}s")
    print("\nSigned error by target compound (positive = heuristic UNDERestimates real cost):")
    for compound, stats in s["signed_error_by_target_compound"].items():
        if stats["n"] == 0:
            continue
        print(f"  {compound:12s} n={stats['n']:3d}  mean_signed_error={stats['mean_signed_error']}")


if __name__ == "__main__":
    results = run_calibration(num_states=60)
    print_report(results)
