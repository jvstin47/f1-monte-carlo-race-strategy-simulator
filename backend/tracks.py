TRACKS = {
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
        "base_lap_time": 82.5,  # ~1:22.5 race pace
        "pit_stop_time_loss": 24.0,  # Long pit lane
        "pit_loss_variance": 1.2,
        "sc_probability": 0.05,
        "overtake_difficulty_index": 0.80,
        "drs_zones": 3,
        "tire_wear_multiplier": {"soft": 1.0, "medium": 1.0, "hard": 1.0},
    },
    "monaco": {
        "name": "Circuit de Monaco",
        "num_laps": 78,
        "base_lap_time": 74.5,  # ~1:14.5 race pace
        "pit_stop_time_loss": 19.5,  # Short pit lane
        "pit_loss_variance": 1.0,
        "sc_probability": 0.08,  # High SC probability
        "overtake_difficulty_index": 0.05,
        "drs_zones": 1,
        "tire_wear_multiplier": {"soft": 0.8, "medium": 0.8, "hard": 0.8},
    },
    "singapore": {
        "name": "Marina Bay Street Circuit",
        "num_laps": 62,
        "base_lap_time": 100.0,  # ~1:40 race pace
        "pit_stop_time_loss": 23.0,
        "pit_loss_variance": 1.5,  # Street circuit, higher variance
        "sc_probability": 0.07,  # Street circuit, high SC rate
        "overtake_difficulty_index": 0.15,
        "drs_zones": 3,
        "tire_wear_multiplier": {"soft": 0.9, "medium": 0.9, "hard": 0.9},
    },
}

def get_track(track_id: str) -> dict:
    """Get track configuration by ID. Raises KeyError if not found."""
    track_id = track_id.lower()
    if track_id not in TRACKS:
        raise KeyError(f"Unknown track_id: '{track_id}'. Available tracks: {list(TRACKS.keys())}")
    return TRACKS[track_id]

def list_tracks() -> dict:
    """Return all available tracks."""
    return TRACKS
