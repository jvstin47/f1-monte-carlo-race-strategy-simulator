import math
import numpy as np
from typing import Dict, Any, List, Tuple
from simulator import simulate_strategy_vectorized, calculate_tire_degradation
from weather import TRANSITION_MATRIX
from heuristic_evaluator import per_lap_cost, playout_cost, strategic_flexibility_bonus, heuristic_uncertainty

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
            # Pitting for the exact compound already fitted burns a scarce stop for
            # no strategic gain (it's not a real option in practice), and left
            # unfiltered it lets the search waste stops resetting tire age instead
            # of preserving them for a genuine compound change later.
            if comp != state.compound:
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
                 track_evolution_rate: float,
                 rollout_num_simulations: int = 500,
                 fuel_effect_per_lap: float = 0.033,
                 use_hybrid_evaluation: bool = True,
                 late_race_lap_threshold: int = 10,
                 flexibility_weight: float = 0.5):
        """
        use_hybrid_evaluation (v5 Phase 3): when True, newly-expanded tree
        leaves are evaluated with the cheap heuristic_evaluator playout by
        default, escalating to a real Monte Carlo rollout only when a
        strategic-discontinuity or late-race trigger fires (see
        _should_use_high_fidelity). When False, every leaf gets a full
        rollout, matching the original (v4) unconditional behavior -- kept
        as an explicit toggle so v4 and v5 MCTS can be benchmarked
        head-to-head against identical code (see evaluate_mcts.py).
        """
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
        self.rollout_num_simulations = rollout_num_simulations
        self.fuel_effect_per_lap = fuel_effect_per_lap

        self.use_hybrid_evaluation = use_hybrid_evaluation
        self.late_race_lap_threshold = late_race_lap_threshold
        self.flexibility_weight = flexibility_weight

        self.root = None
        self.stats = self._fresh_stats()

    @staticmethod
    def _fresh_stats() -> Dict[str, Any]:
        return {
            "nodes_created": 0,
            "heuristic_evaluations": 0,
            "high_fidelity_rollouts": 0,
            "trigger_counts": {},
        }

    def get_search_stats(self) -> Dict[str, Any]:
        return dict(self.stats)

    def _record_trigger(self, trigger: str):
        self.stats["trigger_counts"][trigger] = self.stats["trigger_counts"].get(trigger, 0) + 1

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
            num_simulations=self.rollout_num_simulations,
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

        # The rollout above resets tire age to 1 for the current compound, so it misses
        # the degradation already "owed" from the tires' actual wear. Add that back using
        # the same degradation curve as the main engine (a one-off cost, not scaled by
        # remaining_laps, since scaling by remaining_laps would penalize a state with a
        # freshly-worn tire and a long remaining stint more than a heavily-worn tire near
        # the end of the race, which is backwards).
        tire_age_penalty = calculate_tire_degradation(state.compound, state.tire_age)
        adjusted_times = times + tire_age_penalty

        return risk_adjusted_reward(adjusted_times, self.risk_aversion)

    def heuristic_eval(self, state: MCTSState) -> float:
        """v5 Phase 3 default leaf evaluation (Phase 5: now risk-aware). Same
        playout policy as rollout_eval (project forward on the current
        compound, no further stops) but priced with heuristic_evaluator's
        closed-form, real per-compound components instead of a Monte Carlo
        run. A closed-form projection has no real variance estimate, so
        `heuristic_uncertainty` supplies a cheap proxy instead -- this used to
        be a documented gap (risk_aversion only affected leaves that
        escalated to a real rollout); now both paths respect it, using the
        same mean + risk*uncertainty convention as risk_adjusted_reward."""
        remaining_laps = self.num_laps - state.lap
        if remaining_laps <= 0:
            return 0.0
        cost = playout_cost(
            state.compound, state.tire_age, state.lap, self.num_laps,
            self.base_lap_time, state.weather_state,
            self.fuel_effect_per_lap, self.track_evolution_rate
        )
        cost += calculate_tire_degradation(state.compound, state.tire_age)  # same pre-existing-wear correction rollout_eval applies
        uncertainty = heuristic_uncertainty(state.compound, state.tire_age, state.weather_state,
                                             remaining_laps, state.is_sc_active)
        return -(cost + self.risk_aversion * uncertainty)

    def _should_use_high_fidelity(self, state: MCTSState, reached_via_action: str) -> Tuple[bool, List[str]]:
        """v5 Phase 3 Branch Evaluator. Escalates to a real Monte Carlo rollout
        on strategic discontinuities (pit stop, active Safety Car, non-dry
        weather) or late-race decisions, where a wrong cheap estimate is most
        costly. Trigger A/B from docs/V5_DESIGN.md section 13 (top-candidate,
        close-heuristic-scores) require sibling comparison that isn't
        available at first expansion; that role is filled instead by the
        Phase 4 top-K adaptive refinement in `search()`, applied once the
        tree has enough visits to know who the candidates even are."""
        triggers = []
        if reached_via_action != "stay_out":
            triggers.append("pit_stop")
        if state.is_sc_active:
            triggers.append("safety_car")
        if state.weather_state != "dry":
            triggers.append("weather")
        if (self.num_laps - state.lap) <= self.late_race_lap_threshold:
            triggers.append("late_race")
        return (len(triggers) > 0), triggers

    def _edge_cost(self, state: MCTSState, action: str) -> float:
        """Real per-lap transition cost for taking `action` at `state` --
        the v5 Phase 2 replacement for the old flat
        `base_lap_time + tire_age * 0.10` heuristic. Phase 5: the
        flexibility bonus is scaled up by risk_aversion -- a risk-averse
        driver should value preserving pit-stop optionality (a hedge against
        bad luck) more than a risk-neutral one, not just penalize variance
        after the fact."""
        pit_loss = self.pit_stop_loss if action != "stay_out" else 0.0
        if state.is_sc_active and pit_loss > 0:
            pit_loss = 8.0

        remaining_stops_after = self.max_stops - state.stops_made - (0 if action == "stay_out" else 1)
        flex_bonus = strategic_flexibility_bonus(
            state.weather_state, remaining_stops_after,
            self.flexibility_weight * (1.0 + self.risk_aversion)
        )

        lap_cost = per_lap_cost(
            state.compound, state.tire_age, state.lap, self.num_laps,
            self.base_lap_time, state.weather_state,
            self.fuel_effect_per_lap, self.track_evolution_rate
        )
        return lap_cost + pit_loss - flex_bonus

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

    def search(self, initial_state: MCTSState, budget: int = 500, refine_top_k: int = 0, refine_sample_weight: int = 3):
        """
        refine_top_k / refine_sample_weight (v5 Phase 4, adaptive budgeting):
        after spending `budget` cheap/hybrid iterations, spend one extra real
        Monte Carlo rollout per top-K root candidate (ranked by visit count,
        i.e. by how much the search already trusts them) and blend it into
        that candidate's running average with `refine_sample_weight` worth of
        samples -- concentrating extra compute on the decision that's about
        to actually be made, instead of spreading it uniformly across the
        whole tree. No-op when refine_top_k=0 (default).
        """
        if self.root is None or self.root.state != initial_state:
            self.root = MCTSStateNode(initial_state)
            self.stats = self._fresh_stats()

        for _ in range(budget):
            self._simulate(self.root)

        if refine_top_k > 0:
            self._refine_top_candidates(refine_top_k, refine_sample_weight)

    def _refine_top_candidates(self, top_k: int, sample_weight: int):
        if not self.root or not self.root.action_children:
            return

        ranked = sorted(self.root.action_children.items(), key=lambda kv: kv[1].visit_count, reverse=True)
        candidates = [an for _, an in ranked[:top_k] if an.visit_count > 0]

        for action_node in candidates:
            next_state = sample_next_state(self.root.state, action_node.action, self.sc_prob)
            future_reward = self.rollout_eval(next_state)
            self.stats["high_fidelity_rollouts"] += 1
            self._record_trigger("adaptive_refinement")

            lap_time = self._edge_cost(self.root.state, action_node.action)
            full_reward = -lap_time + future_reward

            action_node.total_reward += full_reward * sample_weight
            action_node.visit_count += sample_weight
            self.root.visit_count += sample_weight

    def _simulate(self, node: MCTSStateNode, reached_via_action: str = "stay_out") -> float:
        if node.state.lap >= self.num_laps:
            return 0.0

        if len(node.action_children) == 0:
            # Expand
            legal_actions = get_legal_actions(node.state, self.max_stops, self.available_compounds, self.num_laps)
            for act in legal_actions:
                node.action_children[act] = MCTSActionNode(act)
            self.stats["nodes_created"] += 1

            if self.use_hybrid_evaluation:
                use_high_fidelity, triggers = self._should_use_high_fidelity(node.state, reached_via_action)
            else:
                use_high_fidelity, triggers = True, ["classic_mode"]

            if use_high_fidelity:
                reward = self.rollout_eval(node.state)
                self.stats["high_fidelity_rollouts"] += 1
            else:
                reward = self.heuristic_eval(node.state)
                self.stats["heuristic_evaluations"] += 1

            for t in triggers:
                self._record_trigger(t)

            node.visit_count += 1
            return reward

        # Select
        action_node = self.select_action(node)

        # Transition
        next_state = sample_next_state(node.state, action_node.action, self.sc_prob)
        if next_state not in action_node.state_children:
            action_node.state_children[next_state] = MCTSStateNode(next_state)

        next_node = action_node.state_children[next_state]

        future_reward = self._simulate(next_node, reached_via_action=action_node.action)

        # v5 Phase 2: real, per-compound-aware transition cost (replaces the old
        # flat `base_lap_time + tire_age * 0.10` heuristic -- see _edge_cost /
        # heuristic_evaluator.py, and docs/PHASE1_CALIBRATION_RESULTS.md for why).
        lap_time = self._edge_cost(node.state, action_node.action)

        # future_reward (from heuristic_eval / rollout_eval / a deeper _simulate
        # call) is a negative reward (-cost), consistent with risk_adjusted_reward's
        # convention where higher = better. lap_time is a positive cost, so it must
        # be negated here too -- otherwise the accumulated reward's meaning drifts
        # with tree depth (shallow paths stay dominated by the large negative leaf
        # estimate while deep paths trend toward the raw positive total race time),
        # which lets UCB1 lock onto whichever action happens to get explored
        # deepest rather than the fastest one.
        reward = -lap_time + future_reward

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
