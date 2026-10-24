"""
Monte Carlo Tree Search (MCTS) Data Models
Schemas for dynamic mid-race replanning, policy generation, and tree diagnostics.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MCTSRequest(BaseModel):
    """Input payload to trigger an MCTS search and replan."""

    track_id: str = Field("bahrain")
    driver_id: str = Field("generic")
    available_compounds: List[str] = Field(["soft", "medium", "hard"])
    max_stops: int = Field(2, ge=1, le=4)
    risk_aversion: float = Field(0.0, ge=0.0, le=1.0)
    weather_enabled: bool = Field(False)
    weather_start_state: str = Field("dry")
    sc_probability: float = Field(0.04)
    current_lap: Optional[int] = Field(1, description="Lap to replan from")
    current_state_overrides: Optional[Dict[str, Any]] = Field(
        None, description="Overrides for mid-race replanning (compound, tire_age, etc.)"
    )
    search_budget: int = Field(
        1000, ge=10, le=5000, description="MCTS iterations to spend on this decision"
    )
    use_hybrid_evaluation: bool = Field(
        True,
        description="True: cheap heuristic leaves escalating on strategic triggers; False: all real rollouts",
    )
    refine_top_k: int = Field(
        2, ge=0, le=5, description="Number of top root candidates to refine with extra real rollouts"
    )


class PolicyRule(BaseModel):
    """Human-readable pit-wall policy rule generated from search results."""

    condition: str
    action: str


class DecisionNodeInfo(BaseModel):
    """Candidate action statistics at the root decision point."""

    action: str
    expected_time: float
    visit_count: int
    win_rate: float


class DecisionTreeData(BaseModel):
    """Summarized root candidate branch tree for dashboard visualization."""

    state_description: str
    candidates: List[DecisionNodeInfo]


class MCTSResponse(BaseModel):
    """Response payload containing optimal action policy and tree diagnostics."""

    policy: List[PolicyRule]
    expected_time: float
    win_rate_vs_fixed_dp: Optional[float] = None
    decision_tree: DecisionTreeData
    diagnostics: Optional[Dict[str, Any]] = Field(
        None, description="Search statistics: nodes_created, heuristic_evaluations, etc."
    )
