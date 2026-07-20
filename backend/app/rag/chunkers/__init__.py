"""Public interface for splitting legal knowledge-base documents."""

from .base import DocumentChunker
from .recursive import DEFAULT_SEPARATORS, RecursiveDocumentChunker

__all__ = ["DEFAULT_SEPARATORS", "DocumentChunker", "RecursiveDocumentChunker"]
