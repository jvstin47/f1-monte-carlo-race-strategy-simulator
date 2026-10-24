"""
System and Diagnostic Data Models
Schemas for health checks, API metadata, and standardized error responses.
"""

from typing import List, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"


class RootResponse(BaseModel):
    """Root metadata response."""

    status: str
    service: str
    available_compounds: List[str]


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    status: str = "error"
    error_type: str
    detail: str
    path: Optional[str] = None
