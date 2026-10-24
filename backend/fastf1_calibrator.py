"""
Backward compatibility shim re-exporting FastF1 calibrator from app.engine.fastf1_service.
"""

from app.engine.fastf1_service import (
    CALIBRATED_BAHRAIN_2023,
    load_and_calibrate_fastf1,
)

__all__ = [
    "CALIBRATED_BAHRAIN_2023",
    "load_and_calibrate_fastf1",
]
