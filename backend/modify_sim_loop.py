import re

with open('simulator.py', 'r') as f:
    content = f.read()

old_loop = """    sc_matrix = generate_safety_car_matrix(num_simulations, num_laps, sc_probability=sc_probability, seed=seed)
    sc_occurrence_count = int(np.sum(np.any(sc_matrix, axis=1)))

    lap_time_matrix = np.zeros((num_simulations, num_laps))
    sc_pace_lap_time = base_lap_time * 1.35

    for sim_idx in range(num_simulations):
        sim_sc = sc_matrix[sim_idx]
        actual_pit_laps = list(planned_pit_laps)

        if is_reactive_sc and len(actual_pit_laps) > 0:
            for k_idx, target_pl in enumerate(actual_pit_laps):
                min_r_lap = max(2, target_pl - reactive_window)
                sc_laps_in_win = np.where(sim_sc[min_r_lap-1:target_pl])[0]
                if len(sc_laps_in_win) > 0:
                    actual_pit_laps[k_idx] = min_r_lap + sc_laps_in_win[0]
                    break

        for lap_idx in range(1, num_laps + 1):
            is_sc_lap = sim_sc[lap_idx - 1]

            stint_idx = 0
            stint_start_lap = 1
            for p_idx, pl in enumerate(actual_pit_laps):
                if lap_idx > pl:
                    stint_idx = p_idx + 1
                    stint_start_lap = pl + 1
                else:
                    break

            compound = comp_list[min(stint_idx, len(comp_list) - 1)]
            tire_age = lap_idx - stint_start_lap + 1

            is_pit_lap = lap_idx in actual_pit_laps
            pit_loss = (sc_pit_loss if is_sc_lap else pit_stop_time_loss) if is_pit_lap else 0.0

            # Fuel weight effect: Fuel is heaviest on Lap 1, lightest on Lap N
            fuel_penalty = (fuel_effect_per_lap * (num_laps - lap_idx)) if enable_fuel_model else 0.0

            if is_sc_lap:
                lap_time = sc_pace_lap_time + pit_loss + random_variations[sim_idx, lap_idx - 1] * 0.2
            else:
                deg = calculate_tire_degradation(compound, tire_age, compound_params)
                lap_time = base_lap_time + deg + fuel_penalty + pit_loss + random_variations[sim_idx, lap_idx - 1]

            lap_time_matrix[sim_idx, lap_idx - 1] = lap_time"""

new_loop = """    sc_matrix = generate_safety_car_matrix(num_simulations, num_laps, sc_probability=sc_probability, seed=seed)
    sc_occurrence_count = int(np.sum(np.any(sc_matrix, axis=1)))

    if weather_enabled:
        weather_matrix = generate_weather_matrix(num_simulations, num_laps, start_state=weather_start_state, seed=seed)
    else:
        weather_matrix = np.zeros((num_simulations, num_laps), dtype=np.int8)

    lap_time_matrix = np.zeros((num_simulations, num_laps))
    sc_pace_lap_time = base_lap_time * 1.35

    pit_loss_noise = np.random.normal(0, pit_loss_variance, size=(num_simulations, num_laps)) if pit_loss_variance > 0 else np.zeros((num_simulations, num_laps))

    for sim_idx in range(num_simulations):
        sim_sc = sc_matrix[sim_idx]
        sim_weather = weather_matrix[sim_idx]
        actual_pit_laps = list(planned_pit_laps)
        sim_comp_list = list(comp_list)

        if is_reactive_sc and len(actual_pit_laps) > 0:
            for k_idx, target_pl in enumerate(actual_pit_laps):
                min_r_lap = max(2, target_pl - reactive_window)
                sc_laps_in_win = np.where(sim_sc[min_r_lap-1:target_pl])[0]
                if len(sc_laps_in_win) > 0:
                    actual_pit_laps[k_idx] = min_r_lap + sc_laps_in_win[0]
                    break

        wet_damp_streak = 0
        weather_pit_triggered = False

        for lap_idx in range(1, num_laps + 1):
            is_sc_lap = sim_sc[lap_idx - 1]
            weather_state = sim_weather[lap_idx - 1]
            
            # Weather logic
            if weather_enabled:
                if weather_state in [1, 2]: # damp or wet
                    wet_damp_streak += 1
                else:
                    wet_damp_streak = 0

                stint_idx_for_check = sum([1 for pl in actual_pit_laps if lap_idx > pl])
                current_compound_check = sim_comp_list[min(stint_idx_for_check, len(sim_comp_list) - 1)]

                if wet_damp_streak >= weather_pit_threshold and current_compound_check in ["soft", "medium", "hard"]:
                    # Trigger reactive pit for intermediates
                    if lap_idx not in actual_pit_laps:
                        actual_pit_laps.append(lap_idx)
                        actual_pit_laps.sort()
                        # Replace subsequent compounds with intermediate
                        idx_to_replace = actual_pit_laps.index(lap_idx)
                        sim_comp_list.insert(idx_to_replace + 1, "intermediate")
                        wet_damp_streak = 0
                        weather_pit_triggered = True

            stint_idx = 0
            stint_start_lap = 1
            for p_idx, pl in enumerate(actual_pit_laps):
                if lap_idx > pl:
                    stint_idx = p_idx + 1
                    stint_start_lap = pl + 1
                else:
                    break

            compound = sim_comp_list[min(stint_idx, len(sim_comp_list) - 1)]
            tire_age = lap_idx - stint_start_lap + 1

            is_pit_lap = lap_idx in actual_pit_laps
            pit_loss = (sc_pit_loss if is_sc_lap else pit_stop_time_loss) if is_pit_lap else 0.0
            if is_pit_lap and pit_loss_variance > 0:
                pit_loss += pit_loss_noise[sim_idx, lap_idx - 1]

            fuel_penalty = (fuel_effect_per_lap * (num_laps - lap_idx)) if enable_fuel_model else 0.0

            if is_sc_lap:
                lap_time = sc_pace_lap_time + pit_loss + random_variations[sim_idx, lap_idx - 1] * 0.2
            else:
                params = compound_params.copy() if compound_params else DEFAULT_COMPOUNDS.get(compound, DEFAULT_COMPOUNDS["medium"]).copy()
                if tire_wear_multiplier:
                    mult = tire_wear_multiplier.get(compound, 1.0)
                    params["wear_rate"] = params.get("wear_rate", 0.08) * mult
                    
                deg = calculate_tire_degradation(compound, tire_age, params)
                weather_penalty = compute_weather_compound_penalty(compound, weather_state) if weather_enabled else 1.0
                
                lap_time = (base_lap_time * weather_penalty) + deg + fuel_penalty + pit_loss + random_variations[sim_idx, lap_idx - 1]

            lap_time_matrix[sim_idx, lap_idx - 1] = lap_time"""

content = content.replace(old_loop, new_loop)

with open('simulator.py', 'w') as f:
    f.write(content)
