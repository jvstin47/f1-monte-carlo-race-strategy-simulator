import numpy as np
from typing import Dict, Tuple

WEATHER_STATES = {"dry": 0, "damp": 1, "wet": 2}
WEATHER_NAMES = {0: "dry", 1: "damp", 2: "wet"}

WEATHER_COMPOUNDS = {
    "intermediate": {"wear_rate": 0.10, "cliff_threshold": 30, "cliff_penalty": 0.015},
    "wet":          {"wear_rate": 0.06, "cliff_threshold": 45, "cliff_penalty": 0.010},
}

TRANSITION_MATRIX = np.array([
    [0.97, 0.03, 0.00],  # from dry
    [0.15, 0.70, 0.15],  # from damp
    [0.05, 0.20, 0.75],  # from wet
])

def generate_weather_matrix(num_simulations: int, num_laps: int, start_state: str = "dry", seed: int = None) -> np.ndarray:
    """
    Generate a (num_simulations, num_laps) matrix of weather states (0=dry, 1=damp, 2=wet).
    Loop over laps (sequential dependency), vectorize across simulations at each step.
    """
    if seed is not None:
        np.random.seed(seed)
    
    start_idx = WEATHER_STATES.get(start_state, 0)
    weather_matrix = np.zeros((num_simulations, num_laps), dtype=np.int8)
    weather_matrix[:, 0] = start_idx

    cum_trans = np.cumsum(TRANSITION_MATRIX, axis=1)
    
    for lap in range(1, num_laps):
        current_states = weather_matrix[:, lap - 1]
        rand_vals = np.random.random(num_simulations)

        for state_idx in range(3):
            mask = current_states == state_idx
            if not np.any(mask):
                continue
            state_rands = rand_vals[mask]

            next_states = np.searchsorted(cum_trans[state_idx], state_rands)
            next_states = np.clip(next_states, 0, 2)
            weather_matrix[mask, lap] = next_states
    
    return weather_matrix

def compute_weather_compound_penalty(compound: str, weather_state: int) -> float:
    """
    Returns lap time MULTIPLIER based on compound/weather mismatch.
    1.0 = optimal, >1.0 = penalty.
    """
    weather_name = WEATHER_NAMES.get(weather_state, "dry")
    
    if weather_name == "dry":
        if compound == "intermediate":
            return 1.25
        elif compound == "wet":
            return 1.40
        else:  # slick compounds
            return 1.0
    elif weather_name == "damp":
        if compound == "intermediate":
            return 1.0
        elif compound == "wet":
            return 1.10
        else:  # slicks in damp
            return 1.35
    elif weather_name == "wet":
        if compound == "wet":
            return 1.0
        elif compound == "intermediate":
            return 1.20
        else:  # slicks in full wet
            return 2.5
    
    return 1.0
