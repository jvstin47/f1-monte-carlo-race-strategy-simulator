"""
Simulation and Optimization Engine Package
Exports simulation functions, tire degradation models, weather matrix generators,
dynamic programming optimizer, MCTS search engine, and telemetry calibration.
"""

from .tire_model import DEFAULT_COMPOUNDS, calculate_tire_degradation
from .weather import (
    WEATHER_STATES,
    WEATHER_NAMES,
    WEATHER_COMPOUNDS,
    TRANSITION_MATRIX,
    generate_weather_matrix,
    compute_weather_compound_penalty,
)
from .simulator import (
    generate_safety_car_matrix,
    parse_strategy_stints,
    simulate_strategy_vectorized,
    summarize_simulation,
    compare_strategies,
    simulate_two_car_undercut,
    analyze_undercut_curve,
)
from .dp_optimizer import optimize_strategy
from .heuristic_evaluator import (
    lap_cost_components,
    per_lap_cost,
    strategic_flexibility_bonus,
    heuristic_uncertainty,
    playout_cost,
)
from .calibration_harness import (
    heuristic_action_cost,
    real_action_cost,
    rank_correlation,
)
from .mcts import (
    MCTSState,
    MCTSActionNode,
    MCTSStateNode,
    MCTSSolver,
    get_legal_actions,
    risk_adjusted_reward,
    sample_next_state,
)
from .fastf1_service import (
    CALIBRATED_BAHRAIN_2023,
    load_and_calibrate_fastf1,
)

__all__ = [
    "DEFAULT_COMPOUNDS",
    "calculate_tire_degradation",
    "WEATHER_STATES",
    "WEATHER_NAMES",
    "WEATHER_COMPOUNDS",
    "TRANSITION_MATRIX",
    "generate_weather_matrix",
    "compute_weather_compound_penalty",
    "generate_safety_car_matrix",
    "parse_strategy_stints",
    "simulate_strategy_vectorized",
    "summarize_simulation",
    "compare_strategies",
    "simulate_two_car_undercut",
    "analyze_undercut_curve",
    "optimize_strategy",
    "lap_cost_components",
    "per_lap_cost",
    "strategic_flexibility_bonus",
    "heuristic_uncertainty",
    "playout_cost",
    "heuristic_action_cost",
    "real_action_cost",
    "rank_correlation",
    "MCTSState",
    "MCTSActionNode",
    "MCTSStateNode",
    "MCTSSolver",
    "get_legal_actions",
    "risk_adjusted_reward",
    "sample_next_state",
    "CALIBRATED_BAHRAIN_2023",
    "load_and_calibrate_fastf1",
]
