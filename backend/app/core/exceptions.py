"""
Custom Application Exceptions and FastAPI Exception Handlers
Provides consistent, structured JSON responses for API errors.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("f1_simulator")


class F1SimulatorError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CircuitNotFoundError(F1SimulatorError):
    """Raised when an unknown circuit track_id is requested."""

    def __init__(self, track_id: str):
        super().__init__(f"Unknown track_id: '{track_id}'", status_code=status.HTTP_404_NOT_FOUND)
        self.track_id = track_id


class DriverNotFoundError(F1SimulatorError):
    """Raised when an unknown driver_id is requested."""

    def __init__(self, driver_id: str):
        super().__init__(f"Unknown driver_id: '{driver_id}'", status_code=status.HTTP_404_NOT_FOUND)
        self.driver_id = driver_id


class SimulationExecutionError(F1SimulatorError):
    """Raised when simulation parameters lead to numerical or logic failures."""

    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


async def f1_simulator_exception_handler(request: Request, exc: F1SimulatorError) -> JSONResponse:
    """Handles all domain-specific F1SimulatorError exceptions."""
    logger.warning("Domain exception on %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error_type": exc.__class__.__name__,
            "detail": exc.message,
            "path": request.url.path,
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected internal server errors."""
    logger.exception("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_type": "InternalServerError",
            "detail": "An unexpected error occurred while processing the simulation request.",
            "path": request.url.path,
        },
    )
