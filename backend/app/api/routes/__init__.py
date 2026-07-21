"""Router composition for the public HTTP API."""

from fastapi import APIRouter

from .ask import router as ask_router
from .health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(ask_router)

__all__ = ["api_v1_router", "health_router"]
