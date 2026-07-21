"""Interfaces, result types, and exceptions for semantic retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeAlias
from collections.abc import Mapping

from langchain_core.documents import Document

MetadataValue: TypeAlias = str | int | float | bool


class RetrievalError(RuntimeError):
    """Base exception for retrieval operations."""


class RetrievalConfigurationError(RetrievalError):
    """Raised when a retriever is configured incorrectly."""


class RetrievalValidationError(ValueError):
    """Raised when a retrieval request is invalid."""


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """One ranked chunk returned by a retriever."""

    document: Document
    metadata: dict[str, Any]
    similarity_score: float
    chunk_id: str
    document_name: str
    category: str


class Retriever(ABC):
    """Retrieve ranked document chunks for a natural-language query."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: Mapping[str, MetadataValue] | None = None,
    ) -> list[RetrievalResult]:
        """Return the most relevant chunks for ``query``."""
