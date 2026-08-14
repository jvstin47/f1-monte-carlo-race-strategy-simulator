"""
v5 Phase 6: Benchmark Suite.

Runs DP vs. v4-classic MCTS vs. v5-hybrid MCTS across the scenario groups from
docs/V5_DESIGN.md section 17, reusing evaluate_mcts.py's real DP/MCTS/simulator
code paths for every scenario (no separate/parallel physics model). Race count
per race-level scenario is reduced from the 100-race canonical run
(docs/PHASE2_4_RESULTS.md) purely to keep total suite runtime bounded -- each
scenario's result notes its own sample size.

Group E (traffic / undercut opportunities) is intentionally NOT covered here:
this codebase's undercut model (simulator.simulate_two_car_undercut) is a
separate two-car engine with no MCTS or DP integration at all -- neither
solver has any notion of a rival car or track position. Benchmarking
"undercut scenarios" against DP/MCTS would mean fabricating a comparison
neither algorithm can actually reason about, so it's documented as out of
scope rather than faked.

Group F (edge cases) doesn't get a DP baseline: DP always plans the full race
from lap 1, so "one pit stop remaining, mid-race" isn't a state DP is ever
actually in. Those scenarios instead compare v4-classic vs. v5-hybrid
solver decisions directly (same pattern as calibration_harness.py), not full
race simulation.

Usage:
    ./venv/bin/python benchmark_suite.py
"""
import json
import time
from typing import Any, Dict, List

from evaluate_mcts import evaluate_mcts_vs_dp
from mcts_optimizer import MCTSSolver, MCTSState

RACE_LEVEL_SCENARIOS = [
    {
        "group": "A - Ordinary dry race",
        "name": "ordinary_dry",
        "kwargs": dict(track_id="bahrain", sc_prob=0.0, weather_start_state="dry"),
    },
    {
        "group": "B - Aggressive tire degradation",
        "name": "aggressive_degradation_silverstone",
        # Silverstone's tire_wear_multiplier (soft 1.2, medium 1.1) is harsher
        # than Bahrain's, stress-testing degradation-driven pit timing more.
        "kwargs": dict(track_id="silverstone", sc_prob=0.03, weather_start_state="dry"),
    },
    {
        "group": "C - Elevated Safety Car frequency",
        "name": "elevated_safety_car",
        "kwargs": dict(track_id="bahrain", sc_prob=0.15, weather_start_state="dry"),
    },
    {
        "group": "D - Weather starting damp",
        "name": "damp_start",
        "kwargs": dict(track_id="bahrain", sc_prob=0.04, weather_start_state="damp"),
    },
    {
        "group": "D - Weather starting wet",
        "name": "wet_start",
        "kwargs": dict(track_id="bahrain", sc_prob=0.04, weather_start_state="wet"),
    },
]

# Group F: direct solver-decision comparisons (v4-classic vs v5-hybrid), no DP
# baseline and no full race simulation -- see module docstring for why.
EDGE_CASE_STATES = [
    {
        "name": "fresh_tires_race_start",
        "state": MCTSState(lap=1, compound="medium", tire_age=1, weather_state="dry", is_sc_active=False, stops_made=0),
    },
    {
        "name": "worn_tires_one_stop_left",
        "state": MCTSState(lap=40, compound="hard", tire_age=22, weather_state="dry", is_sc_active=False, stops_made=1),
    },
    {
        "name": "zero_stops_remaining_late",
        "state": MCTSState(lap=50, compound="hard", tire_age=12, weather_state="dry", is_sc_active=False, stops_made=2),
    },
    {
        "name": "unusual_start_compound_hard_early",
        "state": MCTSState(lap=3, compound="hard", tire_age=3, weather_state="dry", is_sc_active=False, stops_made=0),
    },
    {
        "name": "rain_with_stops_in_reserve",
        "state": MCTSState(lap=20, compound="medium", tire_age=10, weather_state="wet", is_sc_active=False, stops_made=0),
    },
]


def run_race_level_scenarios(num_races: int = 20, mcts_budget: int = 100,
                              mcts_rollout_sims: int = 120, refine_top_k: int = 2,
                              seed: int = 42) -> List[Dict[str, Any]]:
    results = []
    for scenario in RACE_LEVEL_SCENARIOS:
        print(f"\n{'=' * 70}\nScenario: {scenario['group']} ({scenario['name']})\n{'=' * 70}")
        t0 = time.time()
        r = evaluate_mcts_vs_dp(
            num_races=num_races, seed=seed, mcts_budget=mcts_budget,
            mcts_rollout_sims=mcts_rollout_sims, refine_top_k=refine_top_k,
            verbose=False, **scenario["kwargs"]
        )
        exec_t = time.time() - t0
        r["group"] = scenario["group"]
        r["scenario_name"] = scenario["name"]
        r["scenario_kwargs"] = scenario["kwargs"]
        r["suite_exec_seconds"] = round(exec_t, 1)
        results.append(r)

        v4c = r["v4_classic_vs_dp"]
        v5c = r["v5_hybrid_vs_dp"]
        vv = r["v5_hybrid_vs_v4_classic"]
        print(f"  v4 classic vs DP: MCTS {v4c['v4_classic_win_pct']}% / DP {v4c['dp_win_pct']}%, "
              f"mean time saved by MCTS {v4c['mean_time_saved_by_v4_classic']}s")
        print(f"  v5 hybrid  vs DP: MCTS {v5c['v5_hybrid_win_pct']}% / DP {v5c['dp_win_pct']}%, "
              f"mean time saved by MCTS {v5c['mean_time_saved_by_v5_hybrid']}s")
        print(f"  v5 vs v4 classic: v5 {vv['v5_hybrid_win_pct']}% / v4 {vv['v4_classic_win_pct']}%, "
              f"mean time saved by v5 {vv['mean_time_saved_by_v5_hybrid']}s  [{exec_t:.1f}s]")

    return results


def _make_solver(use_hybrid: bool, risk_aversion: float = 0.3, budget_sims: int = 200) -> MCTSSolver:
    return MCTSSolver(
        track_id="bahrain", driver_id="generic", num_laps=57, base_lap_time=94.0,
        pit_stop_loss=22.0, available_compounds=["soft", "medium", "hard", "intermediate", "wet"],
        max_stops=2, sc_prob=0.04, risk_aversion=risk_aversion, weather_enabled=True,
        driver_pace_offset=0.0, driver_consistency=0.15, track_evolution_rate=0.02,
        rollout_num_simulations=budget_sims, use_hybrid_evaluation=use_hybrid,
    )


def run_edge_case_scenarios(search_budget: int = 400, refine_top_k: int = 2) -> List[Dict[str, Any]]:
    print(f"\n{'=' * 70}\nGroup F: Edge cases (v4-classic vs v5-hybrid solver decisions)\n{'=' * 70}")
    results = []
    for case in EDGE_CASE_STATES:
        state = case["state"]

        v4_solver = _make_solver(use_hybrid=False)
        v4_solver.search(state, budget=search_budget)
        v4_action = v4_solver.get_best_action()
        v4_time = -v4_solver.root.action_children[v4_action].get_mean_reward()

        v5_solver = _make_solver(use_hybrid=True)
        v5_solver.search(state, budget=search_budget, refine_top_k=refine_top_k)
        v5_action = v5_solver.get_best_action()
        v5_time = -v5_solver.root.action_children[v5_action].get_mean_reward()

        agree = v4_action == v5_action
        entry = {
            "name": case["name"],
            "state": str(state),
            "v4_classic_action": v4_action,
            "v4_classic_expected_time": round(v4_time, 2),
            "v5_hybrid_action": v5_action,
            "v5_hybrid_expected_time": round(v5_time, 2),
            "agree": agree,
            "v5_diagnostics": v5_solver.get_search_stats(),
        }
        results.append(entry)
        agreement_str = "AGREE" if agree else "DISAGREE"
        print(f"  {case['name']:35s} [{agreement_str}]  v4={v4_action:14s}({v4_time:.1f}s)  "
              f"v5={v5_action:14s}({v5_time:.1f}s)")

    return results


def run_full_suite(num_races: int = 20, search_budget_edge_cases: int = 400) -> Dict[str, Any]:
    race_level = run_race_level_scenarios(num_races=num_races)
    edge_cases = run_edge_case_scenarios(search_budget=search_budget_edge_cases)

    agreement_rate = round(100.0 * sum(e["agree"] for e in edge_cases) / len(edge_cases), 1)

    print(f"\n{'=' * 70}\nSuite Summary\n{'=' * 70}")
    for r in race_level:
        vv = r["v5_hybrid_vs_v4_classic"]
        print(f"  {r['group']:40s} v5 vs v4: {vv['v5_hybrid_win_pct']}% / {vv['v4_classic_win_pct']}%  "
              f"(mean saved by v5: {vv['mean_time_saved_by_v5_hybrid']}s)")
    print(f"  Group F edge cases: v4/v5 agreed on the best action in {agreement_rate}% of {len(edge_cases)} states")

    return {
        "race_level_scenarios": race_level,
        "edge_case_scenarios": edge_cases,
        "edge_case_agreement_rate_pct": agreement_rate,
        "group_e_traffic_undercut": "out of scope -- see module docstring",
    }


if __name__ == "__main__":
    suite_results = run_full_suite(num_races=20)
    with open("benchmark_suite_results.json", "w") as f:
        json.dump(suite_results, f, indent=2, default=str)
    print("\nSaved raw results to benchmark_suite_results.json")
