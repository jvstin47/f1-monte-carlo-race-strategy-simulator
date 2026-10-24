"""Core module containing application configuration and exceptions."""

from .config import settings
from .exceptions import (
    F1SimulatorError,
    CircuitNotFoundError,
    DriverNotFoundError,
    SimulationExecutionError,
    f1_simulator_exception_handler,
    global_exception_handler,
)

__all__ = [
    "settings",
    "F1SimulatorError",
    "CircuitNotFoundError",
    "DriverNotFoundError",
    "SimulationExecutionError",
    "f1_simulator_exception_handler",
    "global_exception_handler",
]
