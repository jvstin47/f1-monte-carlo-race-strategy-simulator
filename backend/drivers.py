"""
Backward compatibility shim re-exporting driver profiles from app.data.drivers.
"""

from app.data.drivers import DRIVER_PROFILES, get_driver, list_drivers

__all__ = ["DRIVER_PROFILES", "get_driver", "list_drivers"]
