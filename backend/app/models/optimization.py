"""
Optimization Data Models
Schemas for dynamic programming backward induction strategy optimization.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .strategy import SimulationResponse


class StintSegment(BaseModel):
    """A single stint in an optimal strategy plan."""

    compound: str
    start_lap: int
    end_lap: int


class OptimizeInput(BaseModel):
    """Input parameters for DP strategy optimization."""

    track_id: str = Field("bahrain")
    available_compounds: List[str] = Field(["soft", "medium", "hard"])
    max_stops: int = Field(2, ge=1, le=4)
    weather_enabled: bool = Field(False)
    weather_start_state: str = Field("dry")
    risk_aversion: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="0 = pick fastest expected strategy; 1 = penalize variance heavily",
    )


class OptimizeResponse(BaseModel):
    """Result of DP optimization including optimal strategy and top alternatives."""

    optimal_strategy: List[StintSegment]
    expected_time: float
    top_5_alternatives: List[Dict[str, Any]]
    monte_carlo_distribution: Optional[SimulationResponse] = None
