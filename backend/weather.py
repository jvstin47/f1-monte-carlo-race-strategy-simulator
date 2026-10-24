"""
Backward compatibility shim re-exporting weather functions from app.engine.weather.
"""

from app.engine.weather import (
    WEATHER_STATES,
    WEATHER_NAMES,
    WEATHER_COMPOUNDS,
    TRANSITION_MATRIX,
    generate_weather_matrix,
    compute_weather_compound_penalty,
)

__all__ = [
    "WEATHER_STATES",
    "WEATHER_NAMES",
    "WEATHER_COMPOUNDS",
    "TRANSITION_MATRIX",
    "generate_weather_matrix",
    "compute_weather_compound_penalty",
]
