import numpy as np
from weather import generate_weather_matrix, compute_weather_compound_penalty

def test_generate_weather_matrix():
    matrix = generate_weather_matrix(num_simulations=10, num_laps=20, start_state="dry", seed=42)
    assert matrix.shape == (10, 20)
    assert matrix[0, 0] == 0  # starts dry

def test_compute_weather_compound_penalty():
    # dry weather, slick tire
    assert compute_weather_compound_penalty("soft", 0) == 1.0
    # dry weather, inter
    assert compute_weather_compound_penalty("intermediate", 0) > 1.0
    # wet weather, wet tire
    assert compute_weather_compound_penalty("wet", 2) == 1.0
    # damp weather, inter
    assert compute_weather_compound_penalty("intermediate", 1) == 1.0
