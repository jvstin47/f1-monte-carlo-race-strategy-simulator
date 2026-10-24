"""
Heuristic Evaluator Module
Provides fast, closed-form, interpretable leaf evaluation for hybrid MCTS search,
avoiding expensive Monte Carlo playouts on non-critical tree nodes.
"""

import math
from typing import Dict

from .tire_model import calculate_tire_degradation, DEFAULT_COMPOUNDS
from .weather import (
    TRANSITION_MATRIX,
    WEATHER_COMPOUNDS,
    WEATHER_STATES,
    compute_weather_compound_penalty,
)

ALL_COMPOUNDS = {**DEFAULT_COMPOUNDS, **WEATHER_COMPOUNDS}


def lap_cost_components(
    compound: str,
    tire_age: int,
    lap: int,
    num_laps: int,
    base_lap_time: float,
    weather_state: str,
    fuel_effect_per_lap: float = 0.033,
    track_evolution_rate: float = 0.02,
) -> Dict[str, float]:
    """Interpretable breakdown of expected costs for one lap on compound at tire_age."""
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


def per_lap_cost(
    compound: str,
    tire_age: int,
    lap: int,
    num_laps: int,
    base_lap_time: float,
    weather_state: str,
    fuel_effect_per_lap: float = 0.033,
    track_evolution_rate: float = 0.02,
) -> float:
    """Total expected per-lap cost excluding pit loss and flexibility bonuses."""
    c = lap_cost_components(
        compound,
        tire_age,
        lap,
        num_laps,
        base_lap_time,
        weather_state,
        fuel_effect_per_lap,
        track_evolution_rate,
    )
    return base_lap_time + c["tire_score"] + c["fuel_score"] + c["weather_score"] + c["track_score"]


def strategic_flexibility_bonus(
    weather_state: str,
    remaining_stops: int,
    flexibility_weight: float = 0.5,
) -> float:
    """Option-value bonus for preserving pit stops under uncertain dry conditions."""
    if remaining_stops <= 0:
        return 0.0
    w_idx = WEATHER_STATES.get(weather_state, 0)
    if w_idx != WEATHER_STATES["dry"]:
        return 0.0
    rain_transition_prob = 1.0 - TRANSITION_MATRIX[w_idx][w_idx]
    return flexibility_weight * remaining_stops * rain_transition_prob


def heuristic_uncertainty(
    compound: str,
    tire_age: int,
    weather_state: str,
    remaining_laps: int,
    is_sc_active: bool = False,
) -> float:
    """Lightweight proxy for point estimate uncertainty when evaluating heuristic leaves."""
    base = 0.05 * max(remaining_laps, 0)
    weather_multiplier = {"dry": 1.0, "damp": 1.6, "wet": 1.4}.get(weather_state, 1.0)
    cliff_threshold = ALL_COMPOUNDS.get(compound, ALL_COMPOUNDS["medium"]).get(
        "cliff_threshold", 24
    )
    cliff_bump = 2.0 if tire_age > cliff_threshold else 0.0
    sc_bump = 3.0 if is_sc_active else 0.0
    return (base * weather_multiplier) + cliff_bump + sc_bump


def playout_cost(
    compound: str,
    tire_age: int,
    lap: int,
    num_laps: int,
    base_lap_time: float,
    weather_state: str,
    fuel_effect_per_lap: float = 0.033,
    track_evolution_rate: float = 0.02,
) -> float:
    """Closed-form projection of remaining-race cost under a naive stay-out playout policy."""
    total = 0.0
    age = tire_age
    for current_lap in range(lap, num_laps + 1):
        total += per_lap_cost(
            compound,
            age,
            current_lap,
            num_laps,
            base_lap_time,
            weather_state,
            fuel_effect_per_lap,
            track_evolution_rate,
        )
        age += 1
    return total
