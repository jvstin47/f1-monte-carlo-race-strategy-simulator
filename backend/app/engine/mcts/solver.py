"""
Monte Carlo Tree Search (MCTS) Solver
Implements UCB1 tree traversal, hybrid leaf evaluation, selective rollouts,
and adaptive refinement for real-time race strategy optimization under uncertainty.
"""

import math
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from .state import (
    MCTSState,
    MCTSActionNode,
    MCTSStateNode,
    get_legal_actions,
    risk_adjusted_reward,
    sample_next_state,
)
from ..simulator import simulate_strategy_vectorized, calculate_tire_degradation
from ..heuristic_evaluator import (
    per_lap_cost,
    playout_cost,
    strategic_flexibility_bonus,
    heuristic_uncertainty,
)


class MCTSSolver:
    """Solves stochastic sequential race strategy decisions via Monte Carlo Tree Search."""

    def __init__(
        self,
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
        flexibility_weight: float = 0.5,
    ):
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

        self.root: Optional[MCTSStateNode] = None
        self.stats: Dict[str, Any] = self._fresh_stats()

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

    def _record_trigger(self, trigger: str) -> None:
        self.stats["trigger_counts"][trigger] = self.stats["trigger_counts"].get(trigger, 0) + 1

    def rollout_eval(self, state: MCTSState) -> float:
        """High-fidelity simulation playout using vectorized Monte Carlo rollouts."""
        remaining_laps = self.num_laps - state.lap
        if remaining_laps <= 0:
            return 0.0

        times, _, _ = simulate_strategy_vectorized(
            compound_1=state.compound,
            pit_lap=999,
            num_laps=remaining_laps,
            base_lap_time=self.base_lap_time,
            pit_stop_time_loss=self.pit_stop_loss,
            num_simulations=self.rollout_num_simulations,
            driver_pace_offset=self.driver_pace_offset,
            driver_consistency=self.driver_consistency,
            sc_probability=self.sc_prob,
            weather_enabled=self.weather_enabled,
            weather_start_state=state.weather_state,
            enable_track_evolution=True,
            track_evolution_rate=self.track_evolution_rate,
            enable_traffic_loss=True,
            enable_fuel_model=True,
        )

        tire_age_penalty = calculate_tire_degradation(state.compound, state.tire_age)
        adjusted_times = times + tire_age_penalty

        return risk_adjusted_reward(adjusted_times, self.risk_aversion)

    def heuristic_eval(self, state: MCTSState) -> float:
        """Fast closed-form leaf evaluator with heuristic uncertainty proxy."""
        remaining_laps = self.num_laps - state.lap
        if remaining_laps <= 0:
            return 0.0
        cost = playout_cost(
            state.compound,
            state.tire_age,
            state.lap,
            self.num_laps,
            self.base_lap_time,
            state.weather_state,
            self.fuel_effect_per_lap,
            self.track_evolution_rate,
        )
        cost += calculate_tire_degradation(state.compound, state.tire_age)
        uncertainty = heuristic_uncertainty(
            state.compound,
            state.tire_age,
            state.weather_state,
            remaining_laps,
            state.is_sc_active,
        )
        return -(cost + self.risk_aversion * uncertainty)

    def _should_use_high_fidelity(
        self, state: MCTSState, reached_via_action: str
    ) -> Tuple[bool, List[str]]:
        """Trigger rules for escalating leaf evaluation to real Monte Carlo rollouts."""
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
        """Computes per-lap edge cost with pit loss and flexibility adjustments."""
        pit_loss = self.pit_stop_loss if action != "stay_out" else 0.0
        if state.is_sc_active and pit_loss > 0:
            pit_loss = 8.0

        remaining_stops_after = self.max_stops - state.stops_made - (
            0 if action == "stay_out" else 1
        )
        flex_bonus = strategic_flexibility_bonus(
            state.weather_state,
            remaining_stops_after,
            self.flexibility_weight * (1.0 + self.risk_aversion),
        )

        lap_cost = per_lap_cost(
            state.compound,
            state.tire_age,
            state.lap,
            self.num_laps,
            self.base_lap_time,
            state.weather_state,
            self.fuel_effect_per_lap,
            self.track_evolution_rate,
        )
        return lap_cost + pit_loss - flex_bonus

    def select_action(self, node: MCTSStateNode, c_param: float = 0.1) -> MCTSActionNode:
        """Selects child action using UCB1 with min-max normalized exploitation term."""
        best_val = -float("inf")
        best_action_node = None

        rewards = [
            an.get_mean_reward()
            for an in node.action_children.values()
            if an.visit_count > 0
        ]
        if len(rewards) >= 2:
            reward_range = max(rewards) - min(rewards)
        else:
            reward_range = 1.0
        if reward_range < 1e-6:
            reward_range = 1.0

        for action_node in node.action_children.values():
            if action_node.visit_count == 0:
                return action_node

            exploit = (action_node.get_mean_reward() - min(rewards)) / reward_range
            explore = c_param * math.sqrt(
                math.log(node.visit_count) / action_node.visit_count
            )
            ucb_val = exploit + explore

            if ucb_val > best_val:
                best_val = ucb_val
                best_action_node = action_node

        return best_action_node

    def search(
        self,
        initial_state: MCTSState,
        budget: int = 500,
        refine_top_k: int = 0,
        refine_sample_weight: int = 3,
    ) -> None:
        """Executes MCTS tree search from initial_state within budget."""
        if self.root is None or self.root.state != initial_state:
            self.root = MCTSStateNode(initial_state)
            self.stats = self._fresh_stats()

        for _ in range(budget):
            self._simulate(self.root)

        if refine_top_k > 0:
            self._refine_top_candidates(refine_top_k, refine_sample_weight)

    def _refine_top_candidates(self, top_k: int, sample_weight: int) -> None:
        if not self.root or not self.root.action_children:
            return

        ranked = sorted(
            self.root.action_children.items(),
            key=lambda kv: kv[1].visit_count,
            reverse=True,
        )
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

    def _simulate(
        self, node: MCTSStateNode, reached_via_action: str = "stay_out"
    ) -> float:
        if node.state.lap >= self.num_laps:
            return 0.0

        if len(node.action_children) == 0:
            legal_actions = get_legal_actions(
                node.state, self.max_stops, self.available_compounds, self.num_laps
            )
            for act in legal_actions:
                node.action_children[act] = MCTSActionNode(act)
            self.stats["nodes_created"] += 1

            if self.use_hybrid_evaluation:
                use_high_fidelity, triggers = self._should_use_high_fidelity(
                    node.state, reached_via_action
                )
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

        action_node = self.select_action(node)
        next_state = sample_next_state(node.state, action_node.action, self.sc_prob)
        if next_state not in action_node.state_children:
            action_node.state_children[next_state] = MCTSStateNode(next_state)

        next_node = action_node.state_children[next_state]
        future_reward = self._simulate(next_node, reached_via_action=action_node.action)

        lap_time = self._edge_cost(node.state, action_node.action)
        reward = -lap_time + future_reward

        action_node.visit_count += 1
        action_node.total_reward += reward
        node.visit_count += 1

        return reward

    def get_best_action(self) -> str:
        """Returns the action with the highest visit count at root."""
        if not self.root or not self.root.action_children:
            return "stay_out"

        best_action = max(
            self.root.action_children.items(), key=lambda x: x[1].visit_count
        )
        return best_action[0]

    def generate_policy_rules(self) -> List[Dict[str, str]]:
        """Synthesizes human-readable pit-wall instructions based on search results."""
        best_act = self.get_best_action()
        rules = []
        if best_act == "stay_out":
            rules.append({
                "condition": f"Lap {self.root.state.lap}, Normal Conditions",
                "action": "Stay Out",
            })
            rules.append({"condition": "If SC triggers", "action": "Pit immediately"})
            if self.weather_enabled:
                rules.append({"condition": "If weather shifts", "action": "Re-evaluate"})
        else:
            comp = best_act.split("_")[1]
            rules.append({
                "condition": f"Lap {self.root.state.lap}",
                "action": f"Pit for {comp.capitalize()}",
            })

        return rules

    def get_decision_tree_data(self) -> Dict[str, Any]:
        """Formats root candidate nodes for dashboard tree inspection."""
        candidates = []
        if self.root:
            for act, act_node in self.root.action_children.items():
                if act_node.visit_count > 0:
                    expected_time = -act_node.get_mean_reward()
                    candidates.append({
                        "action": act,
                        "expected_time": round(expected_time, 2),
                        "visit_count": act_node.visit_count,
                        "win_rate": 0.0,
                    })

        candidates.sort(key=lambda x: x["visit_count"], reverse=True)

        return {
            "state_description": str(self.root.state),
            "candidates": candidates,
        }
