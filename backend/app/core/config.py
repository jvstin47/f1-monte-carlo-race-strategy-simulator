"""
Application Configuration Module
Centralizes environment variable loading and validation with sensible defaults
for development, testing, and production (Render / Railway).
"""

import os
from typing import List


class Settings:
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "F1 Monte Carlo Strategy Simulator"
    VERSION: str = "5.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Server binding
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8005"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # CORS
    _origins_env: str = os.getenv("ALLOWED_ORIGINS", "*")
    ALLOWED_ORIGINS: List[str] = (
        [o.strip() for o in _origins_env.split(",") if o.strip()]
        if _origins_env != "*"
        else ["*"]
    )

    # FastF1 Cache Directory
    FASTF1_CACHE_DIR: str = os.getenv(
        "FASTF1_CACHE_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cache"),
    )

    # Simulation defaults
    DEFAULT_NUM_SIMULATIONS: int = 10000
    DEFAULT_MCTS_BUDGET: int = 1000


settings = Settings()
