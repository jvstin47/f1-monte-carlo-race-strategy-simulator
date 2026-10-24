"""Driver profiles routes."""

from typing import Dict, Any
from fastapi import APIRouter
from ...data.drivers import DRIVER_PROFILES, get_driver

router = APIRouter(prefix="/drivers", tags=["Drivers"])


@router.get("", response_model=Dict[str, Dict[str, Any]])
def get_drivers():
    """Retrieve all available calibrated driver profiles."""
    return DRIVER_PROFILES


@router.get("/{driver_id}")
def get_driver_by_id(driver_id: str):
    """Retrieve driver profile for a specific driver ID code."""
    return get_driver(driver_id)
