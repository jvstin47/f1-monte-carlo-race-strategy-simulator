"""System routes: health check, root metadata."""

from fastapi import APIRouter
from ...models.system import HealthResponse, RootResponse
from ...engine.tire_model import DEFAULT_COMPOUNDS

router = APIRouter(tags=["System"])


@router.get("/", response_model=RootResponse)
def read_root():
    """Returns general service health and available tire compounds."""
    return {
        "status": "online",
        "service": "F1 Monte Carlo Strategy Simulator v4",
        "available_compounds": list(DEFAULT_COMPOUNDS.keys()),
    }


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Lightweight health check endpoint for platform monitoring and cold-start pre-warming."""
    return {"status": "ok"}
