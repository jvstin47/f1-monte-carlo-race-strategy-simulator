import pytest
import numpy as np
from simulator import simulate_strategy_vectorized

def test_fuel_effect():
    # Baseline with NO fuel effect
    baseline_times, _, _ = simulate_strategy_vectorized(
        num_simulations=10, 
        enable_fuel_model=False,
        driver_consistency=0.0,
        sc_probability=0.0
    )
    
    # Fuel effect enabled
    fuel_times, _, _ = simulate_strategy_vectorized(
        num_simulations=10,
        enable_fuel_model=True,
        fuel_effect_per_lap=0.033,
        driver_consistency=0.0,
        sc_probability=0.0
    )
    
    # Fuel effect adds weight penalty, making laps SLOWER (total time higher) over the race compared to a weightless baseline
    # By how much? sum(0.033 * (57 - lap)) for 57 laps = 0.033 * sum(0 to 56) = 0.033 * 1596 = ~52.6 seconds slower
    assert np.mean(fuel_times) > np.mean(baseline_times)
    assert np.isclose(np.mean(fuel_times) - np.mean(baseline_times), 52.6, atol=1.0)

def test_driver_pace_offset():
    baseline_times, _, _ = simulate_strategy_vectorized(
        num_simulations=10,
        driver_consistency=0.0,
        driver_pace_offset=0.0,
        sc_probability=0.0,
        enable_fuel_model=False,
        enable_track_evolution=False,
        enable_traffic_loss=False
    )
    
    fast_times, _, _ = simulate_strategy_vectorized(
        num_simulations=10,
        driver_consistency=0.0,
        driver_pace_offset=-0.5, # 0.5s faster per lap
        sc_probability=0.0,
        enable_fuel_model=False,
        enable_track_evolution=False,
        enable_traffic_loss=False
    )
    
    # Over 57 laps, -0.5s pace offset = 28.5s faster race
    assert np.mean(fast_times) < np.mean(baseline_times)
    assert np.isclose(np.mean(baseline_times) - np.mean(fast_times), 28.5, atol=0.1)

def test_track_evolution_effect():
    baseline_times, _, _ = simulate_strategy_vectorized(
        num_simulations=10,
        enable_track_evolution=False,
        driver_consistency=0.0,
        sc_probability=0.0,
        enable_fuel_model=False,
        enable_traffic_loss=False
    )
    
    evol_times, _, _ = simulate_strategy_vectorized(
        num_simulations=10,
        enable_track_evolution=True,
        track_evolution_rate=0.02,
        driver_consistency=0.0,
        sc_probability=0.0,
        enable_fuel_model=False,
        enable_traffic_loss=False
    )
    
    # Track evolution makes lap times faster
    assert np.mean(evol_times) < np.mean(baseline_times)

def test_traffic_loss():
    baseline_times, _, _ = simulate_strategy_vectorized(
        num_simulations=500, # More sims for stochastic reliability
        enable_traffic_loss=False,
        driver_consistency=0.0,
        sc_probability=0.0,
        enable_fuel_model=False,
        enable_track_evolution=False
    )
    
    traffic_times, _, _ = simulate_strategy_vectorized(
        num_simulations=500,
        enable_traffic_loss=True,
        driver_consistency=0.0,
        sc_probability=0.0,
        enable_fuel_model=False,
        enable_track_evolution=False
    )
    
    # Traffic makes race slower
    assert np.mean(traffic_times) > np.mean(baseline_times)
