"""
Backward compatibility shim re-exporting DP strategy optimizer from app.engine.dp_optimizer.
"""

from app.engine.dp_optimizer import optimize_strategy, trace_strategy

__all__ = ["optimize_strategy", "trace_strategy"]
