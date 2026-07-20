"""Interfaces for converting documents and queries into vector embeddings."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.documents import Document


class DocumentEmbedder(ABC):
    """Create embeddings without coupling generation to vector storage."""

    @abstractmethod
    def embed_documents(self, documents: list[Document]) -> list[list[float]]:
        """Embed documents in input order."""

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """Embed one search query."""
