"""
Tire Degradation and Compound Performance Models
Models wear rates, cliff thresholds, and quadratic cliff penalties for F1 dry tire compounds.
"""

from typing import Dict, Any, Optional

DEFAULT_COMPOUNDS: Dict[str, Dict[str, Any]] = {
    "soft": {
        "wear_rate": 0.14,
        "cliff_threshold": 15,
        "cliff_penalty": 0.03,
    },
    "medium": {
        "wear_rate": 0.08,
        "cliff_threshold": 24,
        "cliff_penalty": 0.02,
    },
    "hard": {
        "wear_rate": 0.04,
        "cliff_threshold": 38,
        "cliff_penalty": 0.01,
    },
}


def calculate_tire_degradation(
    compound_name: str,
    tire_age: int,
    compound_params: Optional[Dict[str, Any]] = None,
) -> float:
    """Calculate lap time penalty in seconds from tire degradation.

    Linear wear before the cliff threshold, transitioning to quadratic penalty post-cliff.
    """
    params = compound_params or DEFAULT_COMPOUNDS.get(
        compound_name.lower(), DEFAULT_COMPOUNDS["medium"]
    )
    wear_rate = params.get("wear_rate", 0.08)
    cliff_threshold = params.get("cliff_threshold", 24)
    cliff_penalty = params.get("cliff_penalty", 0.02)

    deg = wear_rate * tire_age
    if tire_age > cliff_threshold:
        overage = tire_age - cliff_threshold
        deg += cliff_penalty * (overage ** 2)

    return deg
