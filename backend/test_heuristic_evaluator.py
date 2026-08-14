from heuristic_evaluator import lap_cost_components, per_lap_cost, playout_cost, strategic_flexibility_bonus


def test_per_lap_cost_is_compound_aware():
    # The v4 flat heuristic priced soft and hard identically at the same tire
    # age -- the exact defect Phase 1 measured. The real per-lap cost must not.
    soft = per_lap_cost("soft", tire_age=20, lap=20, num_laps=57, base_lap_time=94.0, weather_state="dry")
    hard = per_lap_cost("hard", tire_age=20, lap=20, num_laps=57, base_lap_time=94.0, weather_state="dry")
    assert soft != hard
    assert soft > hard  # soft wears faster (0.14s/lap) than hard (0.04s/lap) at the same age


def test_tire_score_reflects_cliff():
    # Past its cliff threshold, a compound's degradation should accelerate
    # faster than linear -- calculate_tire_degradation already guarantees
    # this; lap_cost_components must expose it, not hide it behind a flat term.
    pre_cliff = lap_cost_components("soft", tire_age=14, lap=14, num_laps=57, base_lap_time=94.0, weather_state="dry")
    post_cliff = lap_cost_components("soft", tire_age=25, lap=25, num_laps=57, base_lap_time=94.0, weather_state="dry")
    per_lap_delta_pre = pre_cliff["tire_score"] / 14
    per_lap_delta_post = post_cliff["tire_score"] / 25
    assert per_lap_delta_post > per_lap_delta_pre


def test_weather_score_penalizes_mismatched_compound():
    slick_in_wet = lap_cost_components("hard", tire_age=5, lap=5, num_laps=57, base_lap_time=94.0, weather_state="wet")
    wet_in_wet = lap_cost_components("wet", tire_age=5, lap=5, num_laps=57, base_lap_time=94.0, weather_state="wet")
    assert slick_in_wet["weather_score"] > wet_in_wet["weather_score"]


def test_playout_cost_sums_per_lap_costs():
    num_laps = 10
    total = playout_cost("medium", tire_age=1, lap=1, num_laps=num_laps, base_lap_time=94.0, weather_state="dry")
    manual = sum(
        per_lap_cost("medium", tire_age=age, lap=lap, num_laps=num_laps, base_lap_time=94.0, weather_state="dry")
        for age, lap in zip(range(1, num_laps + 1), range(1, num_laps + 1))
    )
    assert abs(total - manual) < 1e-9


def test_flexibility_bonus_vanishes_once_wet():
    dry_bonus = strategic_flexibility_bonus("dry", remaining_stops=2)
    wet_bonus = strategic_flexibility_bonus("wet", remaining_stops=2)
    assert dry_bonus > 0
    assert wet_bonus == 0.0


def test_flexibility_bonus_vanishes_with_no_stops_left():
    assert strategic_flexibility_bonus("dry", remaining_stops=0) == 0.0


if __name__ == "__main__":
    test_per_lap_cost_is_compound_aware()
    test_tire_score_reflects_cliff()
    test_weather_score_penalizes_mismatched_compound()
    test_playout_cost_sums_per_lap_costs()
    test_flexibility_bonus_vanishes_once_wet()
    test_flexibility_bonus_vanishes_with_no_stops_left()
    print("All heuristic_evaluator tests passed.")
