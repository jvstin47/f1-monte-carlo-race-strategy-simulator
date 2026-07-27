import time
import numpy as np
from simulator import (
    calculate_tire_degradation, simulate_strategy_vectorized,
    compare_strategies, generate_safety_car_matrix,
    simulate_two_car_undercut, analyze_undercut_curve
)

def test_tire_degradation():
    deg_lap10 = calculate_tire_degradation("soft", 10)
    assert abs(deg_lap10 - 1.4) < 1e-5, f"Expected 1.4, got {deg_lap10}"

    deg_lap20 = calculate_tire_degradation("soft", 20)
    assert abs(deg_lap20 - 3.55) < 1e-5, f"Expected 3.55, got {deg_lap20}"
    print("test_tire_degradation passed.")

def test_multistop_simulation():
    # Test 3-stop strategy: Soft (1-12) -> Soft (13-24) -> Medium (25-40) -> Hard (41-57)
    times, matrix, sc_info = simulate_strategy_vectorized(
        compounds=["soft", "soft", "medium", "hard"],
        pit_laps=[12, 24, 40],
        num_simulations=1000
    )
    assert len(times) == 1000
    assert matrix.shape == (1000, 57)
    assert sc_info["num_stops"] == 3
    print("test_multistop_simulation passed.")

def test_safety_car_generation_and_reactive_pit():
    sc_matrix = generate_safety_car_matrix(1000, 57, sc_probability=0.04)
    assert sc_matrix.shape == (1000, 57)
    races_with_sc = np.sum(np.any(sc_matrix, axis=1))
    assert races_with_sc > 500, f"Expected >500 SC races, got {races_with_sc}"

    res = compare_strategies(
        strategy_a={"compound_1": "medium", "compound_2": "hard", "pit_lap": 25, "sc_probability": 0.08, "is_reactive_sc": True},
        strategy_b={"compound_1": "medium", "compound_2": "hard", "pit_lap": 25, "sc_probability": 0.08, "is_reactive_sc": False},
        num_simulations=5000
    )

    assert res["win_probability_a"] > res["win_probability_b"]
    print(f"test_safety_car_generation_and_reactive_pit passed. Reactive A wins: {res['win_probability_a']}%, Fixed B wins: {res['win_probability_b']}%")

def test_two_car_undercut_model():
    res_undercut = simulate_two_car_undercut(car_a_pit_delta=-2, base_pit_lap_b=22, num_simulations=5000)
    res_overcut = simulate_two_car_undercut(car_a_pit_delta=2, base_pit_lap_b=22, num_simulations=5000)

    assert res_undercut["undercut_win_pct"] > res_overcut["undercut_win_pct"]
    curve = analyze_undercut_curve(base_pit_lap_b=22, num_simulations=2000)
    assert len(curve) == 8
    print(f"test_two_car_undercut_model passed. Undercut 2 laps early win rate: {res_undercut['undercut_win_pct']}%")

if __name__ == "__main__":
    test_tire_degradation()
    test_multistop_simulation()
    test_safety_car_generation_and_reactive_pit()
    test_two_car_undercut_model()
    print("\nAll N-stop simulator tests passed successfully!")
