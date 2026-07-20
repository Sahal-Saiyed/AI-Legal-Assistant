"""Interfaces and domain exceptions for vector persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from langchain_core.documents import Document


class VectorStoreError(RuntimeError):
    """Base exception for vector-store operations."""


class CollectionNotFoundError(VectorStoreError):
    """Raised when an operation requires a collection that does not exist."""


class VectorStoreValidationError(ValueError):
    """Raised when documents or embeddings are invalid for persistence."""


class VectorStore(ABC):
    """Persistence contract for externally generated document embeddings."""

    @abstractmethod
    def create_collection(self) -> None:
        """Create the configured collection if it does not exist."""

    @abstractmethod
    def delete_collection(self) -> None:
        """Delete the configured collection if it exists."""

    @abstractmethod
    def reset_collection(self) -> None:
        """Replace the configured collection with an empty collection."""

    @abstractmethod
    def add_documents(
        self,
        documents: list[Document],
        embeddings: np.ndarray,
    ) -> None:
        """Persist documents and their corresponding embeddings."""

    @abstractmethod
    def count_documents(self) -> int:
        """Return the number of vectors in the configured collection."""

    @abstractmethod
    def collection_exists(self) -> bool:
        """Return whether the configured collection exists."""
