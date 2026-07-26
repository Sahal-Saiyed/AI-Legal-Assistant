"""FastAPI dependency providers for application services."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.auth_config import AuthConfig
from backend.app.database.mongodb import MongoDatabase
from backend.app.schemas.auth import AuthenticatedUser
from backend.app.services.auth_service import AuthService, InvalidTokenError
from backend.app.services.conversation_service import ConversationService
from backend.app.services.document_generation_service import DocumentGenerationService
from backend.app.services import RAGService, RAGServiceConfigurationError

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()


@lru_cache(maxsize=1)
def get_mongo_database() -> MongoDatabase:
    return MongoDatabase(AuthConfig.from_env())


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    config = AuthConfig.from_env()
    database = get_mongo_database()
    return AuthService(database.users, database.sessions, config)


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    return ConversationService(get_mongo_database().conversations)


@lru_cache(maxsize=1)
def get_document_generation_service() -> DocumentGenerationService:
    return DocumentGenerationService(get_mongo_database().generated_documents)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUser:
    try:
        return auth_service.user_from_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


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
