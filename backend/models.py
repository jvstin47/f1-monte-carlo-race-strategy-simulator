from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class StrategyInput(BaseModel):
    
    # v4 fields
    driver_id: str = Field("generic", description="Driver ID for characteristics")
    enable_track_evolution: bool = Field(True, description="Enable track evolution effect")
    enable_traffic_loss: bool = Field(True, description="Enable random traffic loss")
    track_evolution_rate: float = Field(0.02, description="Rate of track evolution")

    # v3 fields
    track_id: str = Field("bahrain", description="Track preset ID (bahrain, silverstone, monza, monaco, singapore)")
    weather_enabled: bool = Field(False, description="Enable stochastic weather simulation")
    weather_start_state: str = Field("dry", description="Starting weather state: dry, wet, or mixed")
    weather_pit_threshold: int = Field(3, ge=1, le=10, description="Consecutive damp/wet laps before reactive weather pit")
    # Legacy 1-stop fields (for backward compatibility)
    compound_1: Optional[str] = Field("soft", description="Starting tire compound (soft, medium, hard)")
    compound_2: Optional[str] = Field("medium", description="Second tire compound after pit stop (soft, medium, hard)")
    pit_lap: Optional[int] = Field(18, ge=1, le=100, description="Lap on which the pit stop occurs")
    
    # N-stop fields (1-stop, 2-stop, 3-stop, 4-stop)
    compounds: Optional[List[str]] = Field(None, description="Sequence of tire compounds per stint e.g. ['soft', 'medium', 'hard']")
    pit_laps: Optional[List[int]] = Field(None, description="List of pit stop laps e.g. [15, 35]")

    num_laps: int = Field(57, ge=1, le=100, description="Total race lap count")
    base_lap_time: float = Field(94.0, gt=0, description="Track baseline lap time in seconds")
    pit_stop_time_loss: float = Field(22.0, ge=0, description="Time lost in pit lane in seconds")
    num_simulations: int = Field(10000, ge=100, le=50000, description="Number of Monte Carlo runs")
    random_std: float = Field(0.15, ge=0, description="Standard deviation of lap variation")
    
    # v2 Safety Car fields
    sc_probability: float = Field(0.04, ge=0.0, le=0.20, description="Per-lap Safety Car trigger probability")
    is_reactive_sc: bool = Field(False, description="If True, pit immediately if SC occurs near target pit lap")
    reactive_window: int = Field(8, ge=1, le=20, description="Lap window before target pit lap to trigger reactive pit under SC")

class CompareInput(BaseModel):
    strategy_a: StrategyInput
    strategy_b: StrategyInput
    num_simulations: Optional[int] = Field(10000, ge=100, le=50000)

class HistogramBin(BaseModel):
    bin_center: float
    count: int
    bin_min: Optional[float] = None
    bin_max: Optional[float] = None

class SimulationSummary(BaseModel):
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    p5: float
    p95: float
    histogram: List[HistogramBin]

class SimulationResponse(BaseModel):
    race_times: List[float]
    summary: SimulationSummary
    strategy: StrategyInput
    sc_info: Optional[Dict[str, Any]] = None

class CombinedHistogramBin(BaseModel):
    bin_center: float
    count_a: int
    count_b: int

class CompareResponse(BaseModel):
    strategy_a_summary: SimulationSummary
    strategy_b_summary: SimulationSummary
    win_probability_a: float
    win_probability_b: float
    combined_histogram: List[CombinedHistogramBin]
    strategy_a: StrategyInput
    strategy_b: StrategyInput
    sc_info_a: Optional[Dict[str, Any]] = None
    sc_info_b: Optional[Dict[str, Any]] = None

class UndercutInput(BaseModel):
    base_pit_lap_b: int = Field(22, ge=5, le=80, description="Target pit lap for defending Car B")
    car_a_compound_1: str = Field("medium")
    car_a_compound_2: str = Field("hard")
    car_b_compound_1: str = Field("medium")
    car_b_compound_2: str = Field("hard")
    initial_gap_seconds: float = Field(1.0, ge=0.0, le=10.0, description="Initial gap in seconds (Car A behind Car B)")
    dirty_air_penalty: float = Field(0.25, ge=0.0, le=1.0, description="Lap time penalty when following within 1.5s")
    num_simulations: int = Field(5000, ge=500, le=20000)

class UndercutPoint(BaseModel):
    pit_delta_laps: int
    pit_lap_a: int
    undercut_win_pct: float
    mean_gap_seconds: float

class UndercutResponse(BaseModel):
    curve_data: List[UndercutPoint]
    base_pit_lap_b: int
    initial_gap_seconds: float
    dirty_air_penalty: float


class StintSegment(BaseModel):
    compound: str
    start_lap: int
    end_lap: int

class OptimizeInput(BaseModel):
    track_id: str = Field("bahrain")
    available_compounds: List[str] = Field(["soft", "medium", "hard"])
    max_stops: int = Field(2, ge=1, le=4)
    weather_enabled: bool = Field(False)
    weather_start_state: str = Field("dry")
    risk_aversion: float = Field(0.0, ge=0.0, le=1.0, description="0 = pick the pure fastest expected strategy; 1 = weigh a candidate's Monte Carlo variance heavily against its speed")

class OptimizeResponse(BaseModel):
    optimal_strategy: List[StintSegment]
    expected_time: float
    top_5_alternatives: List[Dict[str, Any]]
    monte_carlo_distribution: Optional[SimulationResponse] = None

class MCTSRequest(BaseModel):
    track_id: str = Field("bahrain")
    driver_id: str = Field("generic")
    available_compounds: List[str] = Field(["soft", "medium", "hard"])
    max_stops: int = Field(2, ge=1, le=4)
    risk_aversion: float = Field(0.0, ge=0.0, le=1.0)
    weather_enabled: bool = Field(False)
    weather_start_state: str = Field("dry")
    sc_probability: float = Field(0.04)
    current_lap: Optional[int] = Field(1, description="Lap to replan from")
    current_state_overrides: Optional[Dict[str, Any]] = Field(None, description="Overrides for mid-race replanning")
    search_budget: int = Field(1000, ge=10, le=5000, description="MCTS iterations to spend on this decision")
    use_hybrid_evaluation: bool = Field(True, description="v5: cheap heuristic leaves by default, escalating to real Monte Carlo rollouts on strategic triggers. False reproduces v4 behavior (every leaf is a real rollout).")
    refine_top_k: int = Field(2, ge=0, le=5, description="v5 Phase 4: after the main search, spend extra real rollouts refining this many top root candidates. 0 disables.")

class PolicyRule(BaseModel):
    condition: str
    action: str

class DecisionNodeInfo(BaseModel):
    action: str
    expected_time: float
    visit_count: int
    win_rate: float

class DecisionTreeData(BaseModel):
    state_description: str
    candidates: List[DecisionNodeInfo]

class MCTSResponse(BaseModel):
    policy: List[PolicyRule]
    expected_time: float
    win_rate_vs_fixed_dp: Optional[float] = None
    decision_tree: DecisionTreeData
    diagnostics: Optional[Dict[str, Any]] = Field(None, description="v5: nodes_created, heuristic_evaluations, high_fidelity_rollouts, trigger_counts from MCTSSolver.get_search_stats()")
