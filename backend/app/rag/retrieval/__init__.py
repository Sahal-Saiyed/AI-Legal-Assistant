"""Public interface for semantic document retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import (
    MetadataValue,
    RetrievalConfigurationError,
    RetrievalError,
    RetrievalResult,
    RetrievalValidationError,
    Retriever,
)

if TYPE_CHECKING:
    from .chroma_retriever import (
        DEFAULT_TOP_K,
        SUPPORTED_FILTER_FIELDS,
        ChromaRetriever,
    )

_CHROMA_EXPORTS = frozenset(
    {
        "DEFAULT_TOP_K",
        "SUPPORTED_FILTER_FIELDS",
        "ChromaRetriever",
    }
)


def __getattr__(name: str) -> Any:
    """Load the Chroma implementation only when retrieval is first requested."""
    if name not in _CHROMA_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from . import chroma_retriever

    value = getattr(chroma_retriever, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Include lazily exported names in interactive module inspection."""
    return sorted((*globals(), *_CHROMA_EXPORTS))

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
