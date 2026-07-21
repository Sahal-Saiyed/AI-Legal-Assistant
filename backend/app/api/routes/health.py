"""Lightweight process health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, status

from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check API health",
    description="Return process health without checking external dependencies.",
)
def health_check() -> HealthResponse:
    """Return a static process-level health response."""
    return HealthResponse(status="healthy")
