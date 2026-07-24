"""FastAPI application entry point for the AI Legal Assistant."""

from __future__ import annotations

import logging
import os
from time import perf_counter

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.app.api.routes import api_v1_router, health_router
from backend.app.services import (
    RAGGenerationError,
    RAGServiceError,
    RAGValidationError,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Legal Assistant API",
    version="1.0.0",
    description=(
        "A retrieval-augmented API that answers legal questions using curated "
        "Indian-law source documents."
    ),
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)

app.include_router(api_v1_router)
app.include_router(health_router)


@app.middleware("http")
async def log_http_request(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Log request path, status, and duration without logging request content."""
    started_at = perf_counter()
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.info("Incoming HTTP request | method=%s | path=%s", request.method, request.url.path)
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        logger.info(
            "Completed HTTP request | method=%s | path=%s | status=%d | duration=%.3fs",
            request.method,
            request.url.path,
            status_code,
            perf_counter() - started_at,
        )


@app.exception_handler(RAGValidationError)
async def handle_rag_validation_error(
    request: Request,
    exception: RAGValidationError,
) -> JSONResponse:
    """Map service request validation failures to HTTP 400."""
    logger.warning("RAG request validation failed | path=%s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exception)},
    )


@app.exception_handler(RAGGenerationError)
async def handle_rag_generation_error(
    request: Request,
    exception: RAGGenerationError,
) -> JSONResponse:
    """Map upstream model failures to HTTP 502."""
    logger.error("RAG generation failed | path=%s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(exception)},
    )


@app.exception_handler(RAGServiceError)
async def handle_rag_service_error(
    request: Request,
    exception: RAGServiceError,
) -> JSONResponse:
    """Map retrieval, processing, and configuration failures to HTTP 500."""
    logger.error(
        "RAG service failed | path=%s | error_type=%s",
        request.url.path,
        type(exception).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exception)},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Return a stable JSON response for unexpected server failures."""
    logger.error(
        "Unexpected API failure | path=%s | error_type=%s",
        request.url.path,
        type(exception).__name__,
        exc_info=(type(exception), exception, exception.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
