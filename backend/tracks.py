"""
Backward compatibility shim re-exporting track catalog from app.data.tracks.
"""

from app.data.tracks import TRACKS, get_track, list_tracks

__all__ = ["TRACKS", "get_track", "list_tracks"]
