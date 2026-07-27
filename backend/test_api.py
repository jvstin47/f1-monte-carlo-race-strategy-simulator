from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "v3" in response.json()["service"]

def test_simulate_sc_endpoint():
    payload = {
        "compound_1": "soft",
        "compound_2": "medium",
        "pit_lap": 18,
        "sc_probability": 0.05,
        "is_reactive_sc": True,
        "reactive_window": 8
    }
    response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "sc_info" in data
    assert data["sc_info"]["is_reactive_sc"] is True

def test_undercut_analysis_endpoint():
    payload = {
        "base_pit_lap_b": 22,
        "car_a_compound_1": "medium",
        "car_a_compound_2": "hard",
        "initial_gap_seconds": 1.0,
        "dirty_air_penalty": 0.25,
        "num_simulations": 1000
    }
    response = client.post("/undercut-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["curve_data"]) > 0

def test_fastf1_calibrate_endpoint():
    response = client.get("/fastf1/calibrate")
    assert response.status_code == 200
    data = response.json()
    assert "base_lap_time" in data
    assert "compounds" in data

if __name__ == "__main__":
    test_root()
    test_simulate_sc_endpoint()
    test_undercut_analysis_endpoint()
    test_fastf1_calibrate_endpoint()
    print("\nAll v2 API endpoint tests passed successfully!")
