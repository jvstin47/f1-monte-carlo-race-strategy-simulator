import pytest
from tracks import get_track, list_tracks, TRACKS

def test_list_tracks():
    tracks = list_tracks()
    assert len(tracks) == 5
    assert "bahrain" in tracks
    assert "monaco" in tracks

def test_get_track_valid():
    bahrain = get_track("bahrain")
    assert bahrain["name"] == "Bahrain International Circuit"
    assert bahrain["num_laps"] == 57

def test_get_track_invalid():
    with pytest.raises(KeyError):
        get_track("unknown_track")
