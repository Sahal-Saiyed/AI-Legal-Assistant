"""FastAPI dependency providers for application services."""

from __future__ import annotations

import logging
from functools import lru_cache

from backend.app.services import RAGService, RAGServiceConfigurationError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """Create and reuse the expensive production RAG service instance."""
    try:
        service = RAGService.from_env()
    except RAGServiceConfigurationError:
        raise
    except Exception as exc:
        logger.exception("Failed to initialize the RAG service dependency")
        raise RAGServiceConfigurationError(
            "Failed to initialize the RAG service"
        ) from exc

    logger.info("Initialized reusable RAG service dependency")
    return service
