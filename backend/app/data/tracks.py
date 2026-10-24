"""
Circuits and Track Presets Data Catalog
Contains circuit parameters: lap counts, base pace, pit stop loss, SC probability, and tire multipliers.
"""

from typing import Dict, Any, List

TRACKS: Dict[str, Dict[str, Any]] = {
    "bahrain": {
        "name": "Bahrain International Circuit",
        "num_laps": 57,
        "base_lap_time": 94.0,
        "pit_stop_time_loss": 22.0,
        "pit_loss_variance": 0.8,
        "sc_probability": 0.04,
        "overtake_difficulty_index": 0.65,
        "drs_zones": 3,
        "tire_wear_multiplier": {"soft": 1.1, "medium": 1.0, "hard": 1.0},
    },
    "silverstone": {
        "name": "Silverstone Circuit",
        "num_laps": 52,
        "base_lap_time": 90.0,
        "pit_stop_time_loss": 20.5,
        "pit_loss_variance": 0.6,
        "sc_probability": 0.03,
        "overtake_difficulty_index": 0.55,
        "drs_zones": 2,
        "tire_wear_multiplier": {"soft": 1.2, "medium": 1.1, "hard": 1.0},
    },
    "monza": {
        "name": "Autodromo Nazionale Monza",
        "num_laps": 53,
        "base_lap_time": 82.5,
        "pit_stop_time_loss": 24.0,
        "pit_loss_variance": 1.2,
        "sc_probability": 0.05,
        "overtake_difficulty_index": 0.80,
        "drs_zones": 3,
        "tire_wear_multiplier": {"soft": 1.0, "medium": 1.0, "hard": 1.0},
    },
    "monaco": {
        "name": "Circuit de Monaco",
        "num_laps": 78,
        "base_lap_time": 74.5,
        "pit_stop_time_loss": 19.5,
        "pit_loss_variance": 1.0,
        "sc_probability": 0.08,
        "overtake_difficulty_index": 0.05,
        "drs_zones": 1,
        "tire_wear_multiplier": {"soft": 0.8, "medium": 0.8, "hard": 0.8},
    },
    "singapore": {
        "name": "Marina Bay Street Circuit",
        "num_laps": 62,
        "base_lap_time": 100.0,
        "pit_stop_time_loss": 23.0,
        "pit_loss_variance": 1.5,
        "sc_probability": 0.07,
        "overtake_difficulty_index": 0.15,
        "drs_zones": 3,
        "tire_wear_multiplier": {"soft": 0.9, "medium": 0.9, "hard": 0.9},
    },
}


def get_track(track_id: str) -> Dict[str, Any]:
    """Get track configuration by ID. Raises KeyError if not found."""
    if not track_id:
        raise KeyError("Track ID cannot be empty.")
    track_id = track_id.lower()
    if track_id not in TRACKS:
        raise KeyError(f"Unknown track_id: '{track_id}'. Available tracks: {list(TRACKS.keys())}")
    return TRACKS[track_id]


def list_tracks() -> Dict[str, Dict[str, Any]]:
    """Return dictionary of all available track presets."""
    return TRACKS
