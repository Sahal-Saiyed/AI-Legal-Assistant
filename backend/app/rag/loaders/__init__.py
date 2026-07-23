"""Public interface for loading legal knowledge-base documents."""

from .document_loader import (
    DEFAULT_EXCLUDED_DIRECTORIES,
    KnowledgeBaseDocumentLoader,
)

__all__ = ["DEFAULT_EXCLUDED_DIRECTORIES", "KnowledgeBaseDocumentLoader"]
