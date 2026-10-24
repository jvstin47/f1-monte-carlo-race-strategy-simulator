"""
Backward compatibility shim re-exporting simulation engine from app.engine.simulator.
"""

from app.engine.tire_model import DEFAULT_COMPOUNDS, calculate_tire_degradation
from app.engine.simulator import (
    generate_safety_car_matrix,
    parse_strategy_stints,
    simulate_strategy_vectorized,
    summarize_simulation,
    compare_strategies,
    simulate_two_car_undercut,
    analyze_undercut_curve,
)

__all__ = [
    "DEFAULT_COMPOUNDS",
    "calculate_tire_degradation",
    "generate_safety_car_matrix",
    "parse_strategy_stints",
    "simulate_strategy_vectorized",
    "summarize_simulation",
    "compare_strategies",
    "simulate_two_car_undercut",
    "analyze_undercut_curve",
]
