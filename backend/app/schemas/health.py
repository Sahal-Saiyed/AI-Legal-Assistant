"""Response schema for process health checks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Static process-health response."""

    status: Literal["healthy"] = Field(description="Current API process status.")
