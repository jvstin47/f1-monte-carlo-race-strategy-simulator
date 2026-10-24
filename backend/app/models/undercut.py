"""
Undercut Analysis Data Models
Schemas for evaluating two-car track-position delta and pit lap sweep undercut probability.
"""

from typing import List
from pydantic import BaseModel, Field


class UndercutInput(BaseModel):
    """Input parameters for two-car undercut analysis."""

    base_pit_lap_b: int = Field(22, ge=5, le=80, description="Target pit lap for defending Car B")
    car_a_compound_1: str = Field("medium")
    car_a_compound_2: str = Field("hard")
    car_b_compound_1: str = Field("medium")
    car_b_compound_2: str = Field("hard")
    initial_gap_seconds: float = Field(
        1.0, ge=0.0, le=10.0, description="Initial gap in seconds (Car A behind Car B)"
    )
    dirty_air_penalty: float = Field(
        0.25, ge=0.0, le=1.0, description="Lap time penalty when following within 1.5s"
    )
    num_simulations: int = Field(5000, ge=500, le=20000)


class UndercutPoint(BaseModel):
    """Result point corresponding to a single pit lap delta for Car A."""

    pit_delta_laps: int
    pit_lap_a: int
    undercut_win_pct: float
    mean_gap_seconds: float


class UndercutResponse(BaseModel):
    """Complete response payload for an undercut curve evaluation."""

    curve_data: List[UndercutPoint]
    base_pit_lap_b: int
    initial_gap_seconds: float
    dirty_air_penalty: float
