"""Public interface for semantic document retrieval."""

from .base import (
    MetadataValue,
    RetrievalConfigurationError,
    RetrievalError,
    RetrievalResult,
    RetrievalValidationError,
    Retriever,
)
from .chroma_retriever import DEFAULT_TOP_K, SUPPORTED_FILTER_FIELDS, ChromaRetriever

__all__ = [
    "DEFAULT_TOP_K",
    "SUPPORTED_FILTER_FIELDS",
    "ChromaRetriever",
    "MetadataValue",
    "RetrievalConfigurationError",
    "RetrievalError",
    "RetrievalResult",
    "RetrievalValidationError",
    "Retriever",
]
