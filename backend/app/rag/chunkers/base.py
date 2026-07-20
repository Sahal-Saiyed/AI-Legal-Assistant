"""Interfaces for document chunking."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.documents import Document


class DocumentChunker(ABC):
    """Split source documents while preserving their metadata."""

    @abstractmethod
    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Return chunks produced from ``documents``."""
