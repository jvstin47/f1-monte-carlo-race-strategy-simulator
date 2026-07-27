import re

with open('simulator.py', 'r') as f:
    content = f.read()

# 1. Imports
imports = """import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from weather import generate_weather_matrix, compute_weather_compound_penalty, WEATHER_COMPOUNDS
from tracks import get_track
"""
content = re.sub(r"import numpy as np\nfrom typing import Dict, Any, List, Tuple, Optional", imports, content, count=1)

# 2. Remove TRACK_PRESETS
content = re.sub(r"TRACK_PRESETS = \{.*?\n\}\n", "", content, flags=re.DOTALL)

# 3. Add parameters to simulate_strategy_vectorized
new_params = """    compound_params: Dict[str, Any] = None,
    tire_wear_multiplier: Dict[str, float] = None,
    pit_loss_variance: float = 0.0,
    weather_enabled: bool = False,
    weather_start_state: str = "dry",
    weather_pit_threshold: int = 3,
    seed: int = None"""
content = re.sub(r"    compound_params: Dict\[str, Any\] = None,\n    seed: int = None", new_params, content)

# 4. Same for compare_strategies
comp_params = """    compound_params: Dict[str, Any] = None,
    tire_wear_multiplier: Dict[str, float] = None,
    pit_loss_variance: float = 0.0,
    weather_enabled: bool = False,
    weather_start_state: str = "dry",
    weather_pit_threshold: int = 3,
    seed: int = 42"""
content = re.sub(r"    compound_params=strategy_b.get\(\"compound_params\"\),\n        seed=seed\n    \)\n\n    summary_a", "    compound_params=strategy_b.get(\"compound_params\"),\n        tire_wear_multiplier=strategy_b.get(\"tire_wear_multiplier\"),\n        pit_loss_variance=strategy_b.get(\"pit_loss_variance\", 0.0),\n        weather_enabled=strategy_b.get(\"weather_enabled\", False),\n        weather_start_state=strategy_b.get(\"weather_start_state\", \"dry\"),\n        weather_pit_threshold=strategy_b.get(\"weather_pit_threshold\", 3),\n        seed=seed\n    )\n\n    summary_a", content)
content = re.sub(r"    compound_params=strategy_a.get\(\"compound_params\"\),\n        seed=seed\n    \)", "    compound_params=strategy_a.get(\"compound_params\"),\n        tire_wear_multiplier=strategy_a.get(\"tire_wear_multiplier\"),\n        pit_loss_variance=strategy_a.get(\"pit_loss_variance\", 0.0),\n        weather_enabled=strategy_a.get(\"weather_enabled\", False),\n        weather_start_state=strategy_a.get(\"weather_start_state\", \"dry\"),\n        weather_pit_threshold=strategy_a.get(\"weather_pit_threshold\", 3),\n        seed=seed\n    )", content)

content = re.sub(r"    seed: int = 42\n\) -> Dict\[str, Any\]:", comp_params + "\n) -> Dict[str, Any]:", content)

with open('simulator.py', 'w') as f:
    f.write(content)
