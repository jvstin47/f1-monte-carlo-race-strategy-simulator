"""
MCTS State and Action Representations
Defines tree nodes, state transitions, and legal action generation for MCTS.
"""

from typing import Dict, List, Optional
import numpy as np

from ..weather import TRANSITION_MATRIX


class MCTSState:
    """Represents a discrete race state during Monte Carlo Tree Search."""

    def __init__(
        self,
        lap: int,
        compound: str,
        tire_age: int,
        weather_state: str,
        is_sc_active: bool,
        stops_made: int,
    ):
        self.lap = lap
        self.compound = compound
        self.tire_age = tire_age
        self.weather_state = weather_state
        self.is_sc_active = is_sc_active
        self.stops_made = stops_made

    def __hash__(self) -> int:
        return hash((
            self.lap,
            self.compound,
            self.tire_age,
            self.weather_state,
            self.is_sc_active,
            self.stops_made,
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MCTSState):
            return False
        return (
            self.lap,
            self.compound,
            self.tire_age,
            self.weather_state,
            self.is_sc_active,
            self.stops_made,
        ) == (
            other.lap,
            other.compound,
            other.tire_age,
            other.weather_state,
            other.is_sc_active,
            other.stops_made,
        )

    def __str__(self) -> str:
        return (
            f"L{self.lap} | {self.compound.upper()} (Age {self.tire_age}) | "
            f"W:{self.weather_state} | SC:{self.is_sc_active} | Stops:{self.stops_made}"
        )


class MCTSActionNode:
    """Represents an action edge emanating from an MCTS state node."""

    def __init__(self, action: str):
        self.action = action
        self.visit_count = 0
        self.total_reward = 0.0
        self.state_children: Dict[MCTSState, "MCTSStateNode"] = {}

    def get_mean_reward(self) -> float:
        if self.visit_count == 0:
            return 0.0
        return self.total_reward / self.visit_count


class MCTSStateNode:
    """Represents a state node in the MCTS tree with action edges."""

    def __init__(self, state: MCTSState):
        self.state = state
        self.visit_count = 0
        self.action_children: Dict[str, MCTSActionNode] = {}
        self.is_terminal = False


def get_legal_actions(
    state: MCTSState,
    max_stops: int,
    available_compounds: List[str],
    num_laps: int = 57,
) -> List[str]:
    """Determine all legal actions from state given pit-stop constraints."""
    if state.lap >= num_laps:
        return []

    actions = ["stay_out"]
    if state.stops_made < max_stops:
        for comp in available_compounds:
            if comp != state.compound:
                actions.append(f"pit_{comp}")
    return actions


def risk_adjusted_reward(race_times: np.ndarray, risk_aversion: float = 0.0) -> float:
    """Calculate negative expected time with variance penalty scaled by risk_aversion."""
    mean_time = np.mean(race_times)
    std_time = np.std(race_times)
    return -(mean_time + risk_aversion * std_time)


def sample_next_state(state: MCTSState, action: str, sc_prob: float) -> MCTSState:
    """Sample environmental transition (weather and SC) for the chosen action."""
    next_lap = state.lap + 1

    if action == "stay_out":
        next_compound = state.compound
        next_age = state.tire_age + 1
        next_stops = state.stops_made
    else:
        next_compound = action.split("_")[1]
        next_age = 1
        next_stops = state.stops_made + 1

    w_idx = 0 if state.weather_state == "dry" else (1 if state.weather_state == "damp" else 2)
    probs = TRANSITION_MATRIX[w_idx]
    next_w_idx = np.random.choice([0, 1, 2], p=probs)
    next_weather = ["dry", "damp", "wet"][next_w_idx]

    next_sc = np.random.random() < sc_prob

    return MCTSState(next_lap, next_compound, next_age, next_weather, next_sc, next_stops)
