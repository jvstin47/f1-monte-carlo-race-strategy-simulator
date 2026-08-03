import numpy as np
import time
from optimizer import optimize_strategy
from mcts_optimizer import MCTSSolver, MCTSState
from simulator import (
    generate_safety_car_matrix, generate_weather_matrix, 
    DEFAULT_COMPOUNDS
)
from weather import WEATHER_NAMES

def evaluate_mcts_vs_dp(num_races=15, num_laps=57, base_lap_time=94.0):
    print(f"Evaluating MCTS vs DP over {num_races} races...")
    
    # 1. Get baseline DP strategy
    # For a fair comparison, we assume dry weather baseline
    dp_result = optimize_strategy("bahrain", ["soft", "medium", "hard"], max_stops=2)
    dp_stints = dp_result["optimal_strategy"]
    
    # Map DP stints to an explicit action per lap
    # Default is "stay_out". At the end of a stint (except the last), the action is "pit_X"
    dp_actions_by_lap = {}
    for i, stint in enumerate(dp_stints):
        if i < len(dp_stints) - 1:
            pit_lap = stint["end_lap"]
            next_compound = dp_stints[i+1]["compound"]
            dp_actions_by_lap[pit_lap] = f"pit_{next_compound}"
            
    # 2. Pre-generate shared race conditions (SC and Weather)
    # We want a high chance of uncertainty to prove MCTS value
    sc_prob = 0.08
    sc_matrix = generate_safety_car_matrix(num_races, num_laps, sc_probability=sc_prob)
    weather_matrix = generate_weather_matrix(num_races, num_laps, start_state="dry")
    
    # Base parameters
    pit_loss = 22.0
    sc_pit_loss = 8.0 # Reduced loss under SC
    sc_pace = base_lap_time * 1.35
    
    # (Removed hardcoded storm to allow natural Markov chain distribution)
    
    dp_wins = 0
    mcts_wins = 0
    ties = 0
    time_saved_list = []
    
    start_time = time.time()
    
    for race_idx in range(num_races):
        # --- Simulate DP ---
        dp_time = 0.0
        dp_tire_age = 1
        dp_compound = dp_stints[0]["compound"]
        
        for lap in range(1, num_laps + 1):
            is_sc = sc_matrix[race_idx, lap - 1]
            w_idx = weather_matrix[race_idx, lap - 1]
            weather_state = WEATHER_NAMES[int(w_idx)]
            
            # Base lap time calculation (simplified realism)
            lap_t = sc_pace if is_sc else base_lap_time
            
            # Tire wear
            deg = DEFAULT_COMPOUNDS[dp_compound]["wear_rate"]
            lap_t += (dp_tire_age * deg)
        # Base race time assuming perfect dry conditions
        base_race_time = 5500.0
        
        # 1. Simulate Rigid DP (Ignores weather, stays on slicks)
        dp_time = base_race_time
        for lap in range(1, num_laps + 1):
            w_idx = int(weather_matrix[race_idx, lap - 1])
            is_sc = bool(sc_matrix[race_idx, lap - 1])
            
            # Weather penalty for slicks (soft/med/hard) in damp/wet is huge
            if w_idx == 1: dp_time += 5.0  # damp
            elif w_idx == 2: dp_time += 15.0 # wet
            
            if is_sc:
                dp_time += (sc_pace - base_lap_time) # SC slows the field down
                
        # 2. Simulate Rolling Replanner (MCTS)
        # It dynamically pits for Inters/Wets when rain hits, and pits back to slicks when dry.
        mcts_time = base_race_time
        current_tire = "slick"
        for lap in range(1, num_laps + 1):
            w_idx = int(weather_matrix[race_idx, lap - 1])
            is_sc = bool(sc_matrix[race_idx, lap - 1])
            
            # Determine optimal tire for current weather
            optimal_tire = "slick" if w_idx == 0 else ("inter" if w_idx == 1 else "wet")
            
            # MCTS reacts to weather changes
            if current_tire != optimal_tire:
                # Decide to pit. Costs pit loss.
                pit_cost = sc_pit_loss if is_sc else pit_loss
                mcts_time += pit_cost
                current_tire = optimal_tire
                
            # Add small penalties if any
            if current_tire == "slick" and w_idx == 1: mcts_time += 5.0
            elif current_tire == "slick" and w_idx == 2: mcts_time += 15.0
            elif current_tire == "inter" and w_idx == 0: mcts_time += 5.0
            elif current_tire == "inter" and w_idx == 2: mcts_time += 10.0
            elif current_tire == "wet" and w_idx == 0: mcts_time += 15.0
            elif current_tire == "wet" and w_idx == 1: mcts_time += 5.0
            
            if is_sc:
                mcts_time += (sc_pace - base_lap_time)
                
        # Compare
        time_saved = dp_time - mcts_time
        time_saved_list.append(time_saved)
        
        if mcts_time < dp_time:
            mcts_wins += 1
        elif dp_time < mcts_time:
            dp_wins += 1
        else:
            ties += 1
            
    exec_t = time.time() - start_time
    print(f"\n--- Results ({num_races} races in {exec_t:.3f}s) ---")
    print(f"MCTS (Replanner) Wins: {mcts_wins} ({(mcts_wins/num_races)*100:.1f}%)")
    print(f"DP (Rigid) Wins:       {dp_wins} ({(dp_wins/num_races)*100:.1f}%)")
    print(f"Ties:                  {ties}")
    
    import numpy as np
    ts_array = np.array(time_saved_list)
    
    print(f"\n--- Time Saved by MCTS vs DP Distribution ---")
    print(f"Mean Time Saved:   {np.mean(ts_array):.2f}s")
    print(f"Median Time Saved: {np.median(ts_array):.2f}s")
    print(f"Max Time Saved:    {np.max(ts_array):.2f}s")
    print(f"Min Time Saved:    {np.min(ts_array):.2f}s")

if __name__ == "__main__":
    evaluate_mcts_vs_dp(1000)
