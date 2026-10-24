"""
Strategy and Simulation Data Models
Defines Pydantic schemas for single and head-to-head Monte Carlo strategy simulations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StrategyInput(BaseModel):
    """Input parameters for a single race strategy simulation."""

    # Driver & Realism
    driver_id: str = Field("generic", description="Driver ID for characteristics")
    enable_track_evolution: bool = Field(True, description="Enable track evolution effect")
    enable_traffic_loss: bool = Field(True, description="Enable random traffic loss")
    track_evolution_rate: float = Field(0.02, description="Rate of track evolution")

    # Track & Weather
    track_id: str = Field(
        "bahrain",
        description="Track preset ID (bahrain, silverstone, monza, monaco, singapore)",
    )
    weather_enabled: bool = Field(False, description="Enable stochastic weather simulation")
    weather_start_state: str = Field("dry", description="Starting weather state: dry, wet, or mixed")
    weather_pit_threshold: int = Field(
        3, ge=1, le=10, description="Consecutive damp/wet laps before reactive weather pit"
    )

    # Legacy 1-stop fields (for backward compatibility)
    compound_1: Optional[str] = Field("soft", description="Starting tire compound (soft, medium, hard)")
    compound_2: Optional[str] = Field("medium", description="Second tire compound after pit stop (soft, medium, hard)")
    pit_lap: Optional[int] = Field(18, ge=1, le=100, description="Lap on which the pit stop occurs")

    # N-stop fields (1-stop, 2-stop, 3-stop, 4-stop)
    compounds: Optional[List[str]] = Field(
        None, description="Sequence of tire compounds per stint e.g. ['soft', 'medium', 'hard']"
    )
    pit_laps: Optional[List[int]] = Field(None, description="List of pit stop laps e.g. [15, 35]")

    num_laps: int = Field(57, ge=1, le=100, description="Total race lap count")
    base_lap_time: float = Field(94.0, gt=0, description="Track baseline lap time in seconds")
    pit_stop_time_loss: float = Field(22.0, ge=0, description="Time lost in pit lane in seconds")
    num_simulations: int = Field(10000, ge=100, le=50000, description="Number of Monte Carlo runs")
    random_std: float = Field(0.15, ge=0, description="Standard deviation of lap variation")

    # Safety Car fields
    sc_probability: float = Field(0.04, ge=0.0, le=0.20, description="Per-lap Safety Car trigger probability")
    is_reactive_sc: bool = Field(False, description="If True, pit immediately if SC occurs near target pit lap")
    reactive_window: int = Field(8, ge=1, le=20, description="Lap window before target pit lap to trigger reactive pit under SC")


class CompareInput(BaseModel):
    """Input parameters for a head-to-head paired Monte Carlo strategy comparison."""

    strategy_a: StrategyInput
    strategy_b: StrategyInput
    num_simulations: Optional[int] = Field(10000, ge=100, le=50000)


class HistogramBin(BaseModel):
    """Represents a single bin in a lap/race time distribution histogram."""

    bin_center: float
    count: int
    bin_min: Optional[float] = None
    bin_max: Optional[float] = None


class SimulationSummary(BaseModel):
    """Key statistical percentiles and moments from a Monte Carlo simulation run."""

    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    p5: float
    p95: float
    histogram: List[HistogramBin]


class SimulationResponse(BaseModel):
    """Full payload returned from a single-strategy Monte Carlo simulation."""

    race_times: List[float]
    summary: SimulationSummary
    strategy: StrategyInput
    sc_info: Optional[Dict[str, Any]] = None


class CombinedHistogramBin(BaseModel):
    """A histogram bin aligning counts for both strategies in a comparison."""

    bin_center: float
    count_a: int
    count_b: int


class CompareResponse(BaseModel):
    """Full payload returned from a head-to-head strategy comparison."""

    strategy_a_summary: SimulationSummary
    strategy_b_summary: SimulationSummary
    win_probability_a: float
    win_probability_b: float
    combined_histogram: List[CombinedHistogramBin]
    strategy_a: StrategyInput
    strategy_b: StrategyInput
    sc_info_a: Optional[Dict[str, Any]] = None
    sc_info_b: Optional[Dict[str, Any]] = None
