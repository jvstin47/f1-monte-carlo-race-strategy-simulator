"""Circuits and track presets routes."""

from typing import Dict, Any
from fastapi import APIRouter
from ...data.tracks import TRACKS, get_track
from ...core.exceptions import CircuitNotFoundError

router = APIRouter(prefix="/tracks", tags=["Circuits"])


@router.get("", response_model=Dict[str, Dict[str, Any]])
def get_tracks():
    """Retrieve all available F1 circuit preset configurations."""
    return TRACKS


@router.get("/{track_id}")
def get_track_by_id(track_id: str):
    """Retrieve circuit details for a specific track preset."""
    try:
        return get_track(track_id)
    except KeyError:
        raise CircuitNotFoundError(track_id)
