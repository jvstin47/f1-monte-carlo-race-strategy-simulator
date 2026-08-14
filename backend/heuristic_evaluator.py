"""
v5 Phase 2: Heuristic Evaluator.

A decomposed, interpretable, CHEAP (no simulate_strategy_vectorized calls) estimate
of per-lap race-state cost, replacing the flat `tire_age * 0.10` approximation the
v4 MCTS tree-traversal heuristic used. Built directly off the Phase 1 calibration
finding (docs/PHASE1_CALIBRATION_RESULTS.md): that formula never looked at compound
identity at all, so `pit_soft` and `pit_hard` priced identically in the same state,
and its action ranking was close to *inverted* relative to the real simulator 40% of
the time (mean rank correlation 0.101, top-1 agreement 41.7%).

Each component is independently interpretable by design (docs/V5_DESIGN.md section 9
requires this explicitly): the heuristic must not silently become another opaque
optimizer.
"""
import math
from typing import Dict

from simulator import calculate_tire_degradation, DEFAULT_COMPOUNDS
from weather import TRANSITION_MATRIX, WEATHER_COMPOUNDS, WEATHER_STATES, compute_weather_compound_penalty

ALL_COMPOUNDS = {**DEFAULT_COMPOUNDS, **WEATHER_COMPOUNDS}


def lap_cost_components(compound: str, tire_age: int, lap: int, num_laps: int,
                         base_lap_time: float, weather_state: str,
                         fuel_effect_per_lap: float = 0.033,
                         track_evolution_rate: float = 0.02) -> Dict[str, float]:
    """Interpretable breakdown of what it costs to run one lap on `compound` at
    `tire_age`, under `weather_state`. Each key is independently meaningful --
    this is the thing a human (or a future debugging session) can read directly,
    not a black-box score."""
    params = ALL_COMPOUNDS.get(compound, ALL_COMPOUNDS.get("medium"))
    tire_score = calculate_tire_degradation(compound, tire_age, params)
    fuel_score = fuel_effect_per_lap * max(num_laps - lap, 0)

    weather_idx = WEATHER_STATES.get(weather_state, 0)
    weather_mult = compute_weather_compound_penalty(compound, weather_idx)
    weather_score = base_lap_time * (weather_mult - 1.0)

    track_score = -track_evolution_rate * math.log1p(max(lap, 0))

    return {
        "tire_score": tire_score,
        "fuel_score": fuel_score,
        "weather_score": weather_score,
        "track_score": track_score,
    }


def per_lap_cost(compound: str, tire_age: int, lap: int, num_laps: int,
                  base_lap_time: float, weather_state: str,
                  fuel_effect_per_lap: float = 0.033,
                  track_evolution_rate: float = 0.02) -> float:
    """Total real, per-compound-aware cost of one lap (no pit loss, no
    strategic-flexibility bonus -- those are transition-specific, added by the
    caller). This is the direct Phase 2 replacement for the old flat
    `base_lap_time + tire_age * 0.10` traversal heuristic."""
    c = lap_cost_components(compound, tire_age, lap, num_laps, base_lap_time,
                             weather_state, fuel_effect_per_lap, track_evolution_rate)
    return base_lap_time + c["tire_score"] + c["fuel_score"] + c["weather_score"] + c["track_score"]


def strategic_flexibility_bonus(weather_state: str, remaining_stops: int,
                                 flexibility_weight: float = 0.5) -> float:
    """Reward (subtracted from cost) for preserving pit stops while weather is
    dry but could turn -- the 'option value' concept from docs/V5_DESIGN.md
    section 11. Scaled by the real dry->rain transition probability, so it
    naturally shrinks to zero once it's already wet/damp (no more uncertainty
    left to hedge) or once no stops remain to preserve.

    `flexibility_weight` is deliberately conservative and NOT empirically
    tuned to convergence -- see docs/PHASE2_4_RESULTS.md for the benchmark
    this was validated against and the tuning note there.
    """
    if remaining_stops <= 0:
        return 0.0
    w_idx = WEATHER_STATES.get(weather_state, 0)
    if w_idx != WEATHER_STATES["dry"]:
        return 0.0  # already wet/damp: no uncertainty left to hedge
    rain_transition_prob = 1.0 - TRANSITION_MATRIX[w_idx][w_idx]
    return flexibility_weight * remaining_stops * rain_transition_prob


def playout_cost(compound: str, tire_age: int, lap: int, num_laps: int,
                  base_lap_time: float, weather_state: str,
                  fuel_effect_per_lap: float = 0.033,
                  track_evolution_rate: float = 0.02) -> float:
    """Cheap projection of total remaining-race cost from `lap` through
    `num_laps`, assuming no further pit stops -- the same 'naive stay-out'
    playout policy MCTSSolver.rollout_eval's real Monte Carlo rollout uses,
    just priced with these closed-form components instead of running the
    vectorized simulator. This is the default (non-escalated) leaf evaluation
    for the v5 hybrid MCTS -- see mcts_optimizer.MCTSSolver._simulate /
    heuristic_eval."""
    total = 0.0
    age = tire_age
    for current_lap in range(lap, num_laps + 1):
        total += per_lap_cost(compound, age, current_lap, num_laps, base_lap_time,
                               weather_state, fuel_effect_per_lap, track_evolution_rate)
        age += 1
    return total
