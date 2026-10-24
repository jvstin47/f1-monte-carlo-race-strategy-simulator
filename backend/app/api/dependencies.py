"""
API Dependencies and Parameter Resolvers
Resolves preset track parameters and driver characteristics onto simulation inputs.
"""

from typing import Dict, Any

from ..models.strategy import StrategyInput
from ..data.tracks import get_track
from ..data.drivers import get_driver


def resolve_track_params(input_data: StrategyInput) -> Dict[str, Any]:
    """Merge track and driver preset catalog parameters with user inputs."""
    data = input_data.model_dump()

    if input_data.track_id:
        try:
            track = get_track(input_data.track_id)
            data["num_laps"] = track["num_laps"]
            data["base_lap_time"] = track["base_lap_time"]
            data["pit_stop_time_loss"] = track["pit_stop_time_loss"]
            data["sc_probability"] = track.get("sc_probability", data.get("sc_probability", 0.04))
            data["tire_wear_multiplier"] = track.get("tire_wear_multiplier", {})
            data["pit_loss_variance"] = track.get("pit_loss_variance", 0.0)
        except KeyError:
            pass

    if data.get("driver_id") and data["driver_id"].lower() != "generic":
        driver = get_driver(data["driver_id"])
        data["driver_pace_offset"] = driver["pace_offset"]
        data["driver_consistency"] = driver["consistency"]
    else:
        data["driver_pace_offset"] = 0.0
        data["driver_consistency"] = data.get("random_std", 0.15)

    return data
