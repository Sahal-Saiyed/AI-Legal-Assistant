"""Public interface for persistent vector storage."""

from .base import (
    CollectionNotFoundError,
    VectorStore,
    VectorStoreError,
    VectorStoreValidationError,
)
from .chroma_store import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_DATABASE_PATH,
    DEFAULT_INSERT_BATCH_SIZE,
    ChromaVectorStore,
)

__all__ = [
    "CollectionNotFoundError",
    "DEFAULT_COLLECTION_NAME",
    "DEFAULT_DATABASE_PATH",
    "DEFAULT_INSERT_BATCH_SIZE",
    "ChromaVectorStore",
    "VectorStore",
    "VectorStoreError",
    "VectorStoreValidationError",
]
