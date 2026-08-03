import math
import numpy as np
from typing import Dict, Any, List, Tuple
from simulator import simulate_strategy_vectorized
from weather import TRANSITION_MATRIX

class MCTSState:
    def __init__(self, lap: int, compound: str, tire_age: int, weather_state: str, is_sc_active: bool, stops_made: int):
        self.lap = lap
        self.compound = compound
        self.tire_age = tire_age
        self.weather_state = weather_state
        self.is_sc_active = is_sc_active
        self.stops_made = stops_made

    def __hash__(self):
        return hash((self.lap, self.compound, self.tire_age, self.weather_state, self.is_sc_active, self.stops_made))

    def __eq__(self, other):
        return (self.lap, self.compound, self.tire_age, self.weather_state, self.is_sc_active, self.stops_made) == (
            other.lap, other.compound, other.tire_age, other.weather_state, other.is_sc_active, other.stops_made
        )
    
    def __str__(self):
        return f"L{self.lap} | {self.compound.upper()} (Age {self.tire_age}) | W:{self.weather_state} | SC:{self.is_sc_active} | Stops:{self.stops_made}"

class MCTSActionNode:
    def __init__(self, action: str):
        self.action = action
        self.visit_count = 0
        self.total_reward = 0.0
        self.state_children: Dict[MCTSState, 'MCTSStateNode'] = {}

    def get_mean_reward(self):
        if self.visit_count == 0:
            return 0.0
        return self.total_reward / self.visit_count

class MCTSStateNode:
    def __init__(self, state: MCTSState):
        self.state = state
        self.visit_count = 0
        self.action_children: Dict[str, MCTSActionNode] = {}
        self.is_terminal = False

def get_legal_actions(state: MCTSState, max_stops: int, available_compounds: List[str], num_laps: int = 57) -> List[str]:
    if state.lap >= num_laps:
        return []
        
    actions = ["stay_out"]
    if state.stops_made < max_stops:
        for comp in available_compounds:
            actions.append(f"pit_{comp}")
    return actions

def risk_adjusted_reward(race_times: np.ndarray, risk_aversion: float = 0.0) -> float:
    # risk_aversion in [0, 1]: 0 = risk-neutral (minimize expected time)
    #                          1 = fully risk-averse (heavily penalize variance)
    mean_time = np.mean(race_times)
    std_time = np.std(race_times)
    return -(mean_time + risk_aversion * std_time)

def sample_next_state(state: MCTSState, action: str, sc_prob: float) -> MCTSState:
    next_lap = state.lap + 1
    
    if action == "stay_out":
        next_compound = state.compound
        next_age = state.tire_age + 1
        next_stops = state.stops_made
    else:
        next_compound = action.split("_")[1]
        next_age = 1
        next_stops = state.stops_made + 1
        
    # Sample Weather
    w_idx = 0 if state.weather_state == "dry" else (1 if state.weather_state == "damp" else 2)
    probs = TRANSITION_MATRIX[w_idx]
    next_w_idx = np.random.choice([0, 1, 2], p=probs)
    next_weather = ["dry", "damp", "wet"][next_w_idx]
    
    # Sample SC (simplified: just lap independent trigger, no duration for tree search to keep branching factor sane)
    next_sc = np.random.random() < sc_prob
    
    return MCTSState(next_lap, next_compound, next_age, next_weather, next_sc, next_stops)

class MCTSSolver:
    def __init__(self, 
                 track_id: str,
                 driver_id: str,
                 num_laps: int,
                 base_lap_time: float,
                 pit_stop_loss: float,
                 available_compounds: List[str],
                 max_stops: int,
                 sc_prob: float,
                 risk_aversion: float,
                 weather_enabled: bool,
                 driver_pace_offset: float,
                 driver_consistency: float,
                 track_evolution_rate: float):
        
        self.track_id = track_id
        self.driver_id = driver_id
        self.num_laps = num_laps
        self.base_lap_time = base_lap_time
        self.pit_stop_loss = pit_stop_loss
        self.available_compounds = available_compounds
        self.max_stops = max_stops
        self.sc_prob = sc_prob
        self.risk_aversion = risk_aversion
        self.weather_enabled = weather_enabled
        
        self.driver_pace_offset = driver_pace_offset
        self.driver_consistency = driver_consistency
        self.track_evolution_rate = track_evolution_rate
        
        self.root = None
        
    def rollout_eval(self, state: MCTSState) -> float:
        """
        Evaluate the state by running the vectorized simulator forward to the end of the race.
        We assume a simple default heuristic for the remaining laps to get a strong baseline estimate.
        """
        remaining_laps = self.num_laps - state.lap
        if remaining_laps <= 0:
            return 0.0 # Race over, no remaining time
            
        # For the remaining race, simulate using the current compound and no further stops as a naive rollout,
        # or 1 optimal stop if stops_made < max_stops.
        # To keep it extremely fast, we just run the vectorized simulator for remaining_laps.
        
        # We can just call simulate_strategy_vectorized with a 1-stop at a heuristic lap if needed,
        # but to save compute in the MCTS loop, a 0-stop to the end on the current tire is the base evaluator.
        # This acts as the "playout" policy.
        
        # Actually, simulate_strategy_vectorized returns TOTAL race time.
        # We only want the remaining time. 
        # But simulate_strategy_vectorized is fast enough. Let's just simulate a full race that forces
        # the same past choices, and use its total time! That correctly accounts for fuel weight etc.
        # We'll just set pit_lap to 999 (no more stops).
        
        times, _, _ = simulate_strategy_vectorized(
            compound_1=state.compound,
            pit_lap=999, # No more stops in rollout
            num_laps=remaining_laps,
            base_lap_time=self.base_lap_time,
            pit_stop_time_loss=self.pit_stop_loss,
            num_simulations=500, # Small batch for rollout
            driver_pace_offset=self.driver_pace_offset,
            driver_consistency=self.driver_consistency,
            sc_probability=self.sc_prob, # SC independent of weather toggle
            weather_enabled=self.weather_enabled,
            weather_start_state=state.weather_state,
            enable_track_evolution=True,
            track_evolution_rate=self.track_evolution_rate,
            enable_traffic_loss=True,
            enable_fuel_model=True
        )
        
        # Add penalty for already accumulated tire age (rough heuristic:
        # each lap of existing wear adds ~0.05s degradation penalty)
        tire_age_penalty = state.tire_age * 0.05 * remaining_laps * 0.5
        adjusted_times = times + tire_age_penalty
        
        return risk_adjusted_reward(adjusted_times, self.risk_aversion)

    def select_action(self, node: MCTSStateNode, c_param: float = 0.1) -> MCTSActionNode:
        best_val = -float('inf')
        best_action_node = None
        
        # Compute reward range for normalization so UCB1 exploration term is meaningful
        rewards = [an.get_mean_reward() for an in node.action_children.values() if an.visit_count > 0]
        if len(rewards) >= 2:
            reward_range = max(rewards) - min(rewards)
        else:
            reward_range = 1.0
        if reward_range < 1e-6:
            reward_range = 1.0  # Avoid division by zero
        
        for action, action_node in node.action_children.items():
            if action_node.visit_count == 0:
                # Force exploration of unvisited actions
                return action_node
            
            # UCB1 formula with normalized exploitation term
            exploit = (action_node.get_mean_reward() - min(rewards)) / reward_range
            explore = c_param * math.sqrt(math.log(node.visit_count) / action_node.visit_count)
            ucb_val = exploit + explore
            
            if ucb_val > best_val:
                best_val = ucb_val
                best_action_node = action_node
                
        return best_action_node

    def search(self, initial_state: MCTSState, budget: int = 500):
        if self.root is None or self.root.state != initial_state:
            self.root = MCTSStateNode(initial_state)
            
        for _ in range(budget):
            self._simulate(self.root)
            
    def _simulate(self, node: MCTSStateNode) -> float:
        if node.state.lap >= self.num_laps:
            return 0.0
            
        if len(node.action_children) == 0:
            # Expand
            legal_actions = get_legal_actions(node.state, self.max_stops, self.available_compounds, self.num_laps)
            for act in legal_actions:
                node.action_children[act] = MCTSActionNode(act)
                
            # Rollout from newly expanded node (just pick first action naively or eval state directly)
            reward = self.rollout_eval(node.state)
            node.visit_count += 1
            return reward
            
        # Select
        action_node = self.select_action(node)
        
        # Transition
        next_state = sample_next_state(node.state, action_node.action, self.sc_prob)
        if next_state not in action_node.state_children:
            action_node.state_children[next_state] = MCTSStateNode(next_state)
            
        next_node = action_node.state_children[next_state]
        
        future_reward = self._simulate(next_node)
        
        # Calculate transition cost (lap time + pit loss) for taking this action
        pit_loss = self.pit_stop_loss if action_node.action != "stay_out" else 0.0
        if node.state.is_sc_active and pit_loss > 0:
            pit_loss = 8.0
            
        # Simplified lap time estimate for the tree traversal cost
        deg_penalty = node.state.tire_age * 0.10
        lap_time = self.base_lap_time + deg_penalty + pit_loss
        
        reward = lap_time + future_reward
        
        # Backpropagate
        action_node.visit_count += 1
        action_node.total_reward += reward
        node.visit_count += 1
        
        return reward

    def get_best_action(self) -> str:
        if not self.root or not self.root.action_children:
            return "stay_out"
            
        best_action = max(self.root.action_children.items(), key=lambda x: x[1].visit_count)
        return best_action[0]
        
    def generate_policy_rules(self) -> List[Dict[str, str]]:
        # A simple heuristic rule set based on the root state
        best_act = self.get_best_action()
        rules = []
        if best_act == "stay_out":
            rules.append({"condition": f"Lap {self.root.state.lap}, Normal Conditions", "action": "Stay Out"})
            rules.append({"condition": f"If SC triggers", "action": "Pit immediately"})
            if self.weather_enabled:
                rules.append({"condition": f"If weather shifts", "action": "Re-evaluate"})
        else:
            comp = best_act.split("_")[1]
            rules.append({"condition": f"Lap {self.root.state.lap}", "action": f"Pit for {comp.capitalize()}"})
            
        return rules
        
    def get_decision_tree_data(self) -> Dict[str, Any]:
        candidates = []
        if self.root:
            for act, act_node in self.root.action_children.items():
                if act_node.visit_count > 0:
                    # Invert the reward back to a positive expected time for display purposes
                    # Since reward = -(mean + risk*std), expected time is approximately -reward
                    expected_time = -act_node.get_mean_reward()
                    candidates.append({
                        "action": act,
                        "expected_time": round(expected_time, 2),
                        "visit_count": act_node.visit_count,
                        "win_rate": 0.0 # Placeholder, can be calculated via side-by-side rollout
                    })
                    
        # Sort by visit count (highest confidence first)
        candidates.sort(key=lambda x: x["visit_count"], reverse=True)
        
        return {
            "state_description": str(self.root.state),
            "candidates": candidates
        }
