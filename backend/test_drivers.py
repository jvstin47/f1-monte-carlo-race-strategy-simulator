import pytest
from drivers import get_driver

def test_get_generic_driver():
    driver = get_driver("generic")
    assert driver["pace_offset"] == 0.0
    assert driver["consistency"] == 0.15

def test_get_verstappen_driver():
    driver = get_driver("ver")
    assert driver["pace_offset"] == -0.15
    assert driver["consistency"] == 0.08
    assert driver["team"] == "Red Bull Racing"
    assert driver["name"] == "Max Verstappen"

def test_get_unknown_driver():
    driver = get_driver("unknown_driver")
    assert driver["name"] == "Generic Driver"
    assert driver["pace_offset"] == 0.0
