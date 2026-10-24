"""API Routes package aggregating all domain route modules."""

from .system import router as system_router
from .circuits import router as circuits_router
from .drivers import router as drivers_router
from .simulation import router as simulation_router
from .optimization import router as optimization_router
from .telemetry import router as telemetry_router

__all__ = [
    "system_router",
    "circuits_router",
    "drivers_router",
    "simulation_router",
    "optimization_router",
    "telemetry_router",
]
