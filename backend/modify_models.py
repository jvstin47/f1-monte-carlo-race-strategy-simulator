import re

with open('models.py', 'r') as f:
    content = f.read()

new_fields = """    
    # v3 fields
    track_id: Optional[str] = Field(None, description="Track preset ID (bahrain, silverstone, monza, monaco, singapore)")
    weather_enabled: bool = Field(False, description="Enable stochastic weather simulation")
    weather_start_state: str = Field("dry", description="Starting weather state: dry, wet, or mixed")
    weather_pit_threshold: int = Field(3, ge=1, le=10, description="Consecutive damp/wet laps before reactive weather pit")
"""
content = re.sub(r"(class StrategyInput\(BaseModel\):\n)", r"\1" + new_fields, content)

new_models = """

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

class OptimizeResponse(BaseModel):
    optimal_strategy: List[StintSegment]
    expected_time: float
    top_5_alternatives: List[Dict[str, Any]]
    monte_carlo_distribution: Optional[SimulationResponse] = None
"""
content += new_models

with open('models.py', 'w') as f:
    f.write(content)
