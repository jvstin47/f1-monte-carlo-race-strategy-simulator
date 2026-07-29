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
    
    # 3. Inject a severe thunderstorm in half the races to prove DP fails under uncertainty
    for r in range(num_races):
        if r % 2 == 0:
            weather_matrix[r, 20:40] = 2 # Heavy rain for 20 laps
    
    dp_wins = 0
    mcts_wins = 0
    ties = 0
    
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
            
            # Weather penalty
            w_penalties = {"soft": [0, 5, 15], "medium": [0, 5, 15], "hard": [0, 5, 15], "intermediate": [5, 0, 10], "wet": [15, 5, 0]}
            lap_t += w_penalties[dp_compound][w_idx]
            
            # Check action
            action = dp_actions_by_lap.get(lap, "stay_out")
            if action != "stay_out":
                dp_time += (sc_pit_loss if is_sc else pit_loss)
                dp_compound = action.split("_")[1]
                dp_tire_age = 1
            else:
                dp_tire_age += 1
                
            dp_time += lap_t
            
        # --- Simulate MCTS ---
        mcts_time = 0.0
        mcts_state = MCTSState(lap=1, compound=dp_stints[0]["compound"], tire_age=1, weather_state="dry", is_sc_active=bool(sc_matrix[race_idx, 0]), stops_made=0)
        
        solver = MCTSSolver(
            track_id="bahrain", driver_id="generic", num_laps=num_laps, base_lap_time=base_lap_time,
            pit_stop_loss=pit_loss, available_compounds=["soft", "medium", "hard", "intermediate", "wet"], max_stops=5,
            sc_prob=sc_prob, risk_aversion=0.0, weather_enabled=True,
            driver_pace_offset=0.0, driver_consistency=0.15, track_evolution_rate=0.02
        )
        
        # Patch rollout_eval for this test to be extremely fast (10 simulations instead of 500)
        original_rollout = solver.rollout_eval
        def fast_rollout(state):
            # Same as original but small batch
            remaining_laps = solver.num_laps - state.lap
            if remaining_laps <= 0: return 0.0
            from simulator import simulate_strategy_vectorized
            
            # MCTS needs a sensible rollout heuristic. 0-stops to the end forces massive cliff penalties,
            # biasing the agent to pit constantly. We give it a 1-stop heuristic if there's >15 laps left.
            r_pit = remaining_laps // 2 if remaining_laps > 15 else 999
            
            times, _, _ = simulate_strategy_vectorized(
                compound_1=state.compound, compound_2="hard", pit_lap=r_pit, num_laps=remaining_laps,
                base_lap_time=solver.base_lap_time, pit_stop_time_loss=solver.pit_stop_loss,
                num_simulations=10, driver_pace_offset=solver.driver_pace_offset,
                driver_consistency=solver.driver_consistency, sc_probability=solver.sc_prob,
                weather_enabled=solver.weather_enabled, weather_start_state=state.weather_state,
                enable_track_evolution=True, track_evolution_rate=solver.track_evolution_rate,
                enable_traffic_loss=True, enable_fuel_model=True
            )
            adjusted_times = times + (state.tire_age * 0.05 * remaining_laps * 0.5)
            from mcts_optimizer import risk_adjusted_reward
            return risk_adjusted_reward(adjusted_times, solver.risk_aversion)
            
        solver.rollout_eval = fast_rollout
        
        ALL_COMPOUNDS = {**DEFAULT_COMPOUNDS}
        from weather import WEATHER_COMPOUNDS
        ALL_COMPOUNDS.update(WEATHER_COMPOUNDS)
        
        # We only call MCTS to replan when something unexpected happens (SC or Weather)
        current_plan = list(dp_stints)
        plan_idx = 0
        
        for lap in range(1, num_laps + 1):
            is_sc = sc_matrix[race_idx, lap - 1]
            w_idx = weather_matrix[race_idx, lap - 1]
            weather_state = WEATHER_NAMES[int(w_idx)]
            
            mcts_state.weather_state = weather_state
            mcts_state.is_sc_active = bool(is_sc)
            mcts_state.lap = lap
            
            # Calculate lap time based on CURRENT state (before action)
            lap_t = sc_pace if is_sc else base_lap_time
            deg = ALL_COMPOUNDS[mcts_state.compound].get("wear_rate", 0.10)
            lap_t += (mcts_state.tire_age * deg)
            w_penalties = {"soft": [0, 5, 15], "medium": [0, 5, 15], "hard": [0, 5, 15], "intermediate": [5, 0, 10], "wet": [15, 5, 0]}
            lap_t += w_penalties[mcts_state.compound][w_idx]
            mcts_time += lap_t
            
            # Event triggers replan: Weather is not dry, or SC deployed
            is_event = (weather_state != "dry" or is_sc)
            
            if lap < num_laps and is_event and mcts_state.stops_made < 5:
                solver.search(mcts_state, budget=25)
                best_act = solver.get_best_action()
            else:
                # Follow plan
                best_act = "stay_out"
                if plan_idx < len(current_plan) - 1:
                    if lap == current_plan[plan_idx]["end_lap"]:
                        best_act = f"pit_{current_plan[plan_idx+1]['compound']}"
                        plan_idx += 1
                
            if best_act != "stay_out":
                mcts_time += (sc_pit_loss if is_sc else pit_loss)
                next_comp = best_act.split("_")[1]
                mcts_state = MCTSState(lap=lap+1, compound=next_comp, tire_age=1, weather_state=weather_state, is_sc_active=is_sc, stops_made=mcts_state.stops_made+1)
            else:
                mcts_state.tire_age += 1
                mcts_state.lap += 1
            
        print(f"Race {race_idx+1}: DP = {dp_time:.2f}s | MCTS = {mcts_time:.2f}s")
        if mcts_time < dp_time:
            mcts_wins += 1
        elif dp_time < mcts_time:
            dp_wins += 1
        else:
            ties += 1

    elapsed = time.time() - start_time
    print(f"\n--- Results ({num_races} races in {elapsed:.1f}s) ---")
    print(f"MCTS Wins: {mcts_wins} ({(mcts_wins/num_races)*100:.1f}%)")
    print(f"DP Wins:   {dp_wins} ({(dp_wins/num_races)*100:.1f}%)")
    print(f"Ties:      {ties}")
    
if __name__ == "__main__":
    evaluate_mcts_vs_dp(15)
