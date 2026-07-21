"""Semantic retrieval from a persistent Chroma collection."""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter
from typing import Any, Final

import chromadb
from chromadb.api.models.Collection import Collection
from langchain_core.documents import Document

from backend.app.rag.embeddings.base import DocumentEmbedder
from backend.app.rag.vectorstore import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_DATABASE_PATH,
    ChromaVectorStore,
)

from .base import (
    MetadataValue,
    RetrievalConfigurationError,
    RetrievalError,
    RetrievalResult,
    RetrievalValidationError,
    Retriever,
)

logger = logging.getLogger(__name__)

DEFAULT_TOP_K: Final[int] = 5
SUPPORTED_FILTER_FIELDS: Final[frozenset[str]] = frozenset(
    {"category", "document_name", "source"}
)
_FILTER_VALUE_TYPES: Final[tuple[type, ...]] = (str, int, float, bool)
_SUPPORTED_DISTANCE_METRICS: Final[frozenset[str]] = frozenset({"cosine", "ip", "l2"})


class ChromaRetriever(Retriever):
    """Embed queries and retrieve ranked chunks from an existing Chroma collection."""

    def __init__(
        self,
        embedder: DocumentEmbedder,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        top_k: int = DEFAULT_TOP_K,
        score_threshold: float | None = None,
        database_path: Path | str = DEFAULT_DATABASE_PATH,
    ) -> None:
        self._validate_embedder(embedder)
        self._validate_top_k(top_k)
        self._validate_score_threshold(score_threshold)

        self._embedder = embedder
        self._top_k = top_k
        self._score_threshold = score_threshold
        self._vector_store = ChromaVectorStore(
            database_path=database_path,
            collection_name=collection_name,
        )
        if not self._vector_store.collection_exists():
            raise RetrievalConfigurationError(
                f"Chroma collection does not exist: {collection_name} "
                f"({self._vector_store.database_path})"
            )
        if self._vector_store.count_documents() == 0:
            raise RetrievalConfigurationError(
                f"Chroma collection is empty: {collection_name}"
            )

        self._client = chromadb.PersistentClient(path=str(self._vector_store.database_path))
        self._collection = self._client.get_collection(name=collection_name)
        self._distance_metric = self._read_distance_metric(self._collection)
        logger.info(
            "Using retrieval collection %s at %s (distance metric: %s)",
            collection_name,
            self._vector_store.database_path,
            self._distance_metric,
        )

    @property
    def collection_name(self) -> str:
        """Name of the collection queried by this retriever."""
        return self._vector_store.collection_name

    @property
    def top_k(self) -> int:
        """Default maximum number of results."""
        return self._top_k

    @property
    def score_threshold(self) -> float | None:
        """Optional minimum similarity score."""
        return self._score_threshold

    @property
    def database_path(self) -> Path:
        """Persistent Chroma database directory."""
        return self._vector_store.database_path

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: Mapping[str, MetadataValue] | None = None,
    ) -> list[RetrievalResult]:
        """Embed ``query`` and return its highest-scoring stored chunks."""
        normalized_query = self._validate_query(query)
        effective_top_k = self._top_k if top_k is None else top_k
        self._validate_top_k(effective_top_k)
        where = self._build_where_filter(filters)

        logger.info(
            "Retrieving from collection %s | query=%r | top_k=%d | filters=%s",
            self.collection_name,
            normalized_query,
            effective_top_k,
            dict(filters) if filters else None,
        )
        started_at = perf_counter()

        try:
            query_embedding = self._embedder.embed_query(normalized_query)
            self._validate_query_embedding(query_embedding)
            available_count = self._vector_store.count_documents()
            raw_result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(effective_top_k, available_count),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            results = self._parse_results(raw_result)
        except (RetrievalError, RetrievalValidationError):
            raise
        except Exception as exc:
            logger.exception("Retrieval failed for collection %s", self.collection_name)
            raise RetrievalError(
                f"Failed to retrieve from Chroma collection {self.collection_name}"
            ) from exc

        if self._score_threshold is not None:
            results = [
                result
                for result in results
                if result.similarity_score >= self._score_threshold
            ]

        duration = perf_counter() - started_at
        average_score = (
            sum(result.similarity_score for result in results) / len(results)
            if results
            else None
        )
        logger.info(
            "Retrieved %d chunk(s) in %.3f seconds | average similarity=%s",
            len(results),
            duration,
            f"{average_score:.6f}" if average_score is not None else "n/a",
        )
        return results

    def _parse_results(self, raw_result: Mapping[str, Any]) -> list[RetrievalResult]:
        ids = self._first_result_row(raw_result, "ids")
        documents = self._first_result_row(raw_result, "documents")
        metadatas = self._first_result_row(raw_result, "metadatas")
        distances = self._first_result_row(raw_result, "distances")

        lengths = {len(ids), len(documents), len(metadatas), len(distances)}
        if len(lengths) != 1:
            raise RetrievalError("Chroma returned result fields with inconsistent lengths")

        results: list[RetrievalResult] = []
        for index, (record_id, content, metadata, distance) in enumerate(
            zip(ids, documents, metadatas, distances, strict=True)
        ):
            if not isinstance(record_id, str) or not record_id:
                raise RetrievalError(f"Chroma result {index} has an invalid ID")
            if not isinstance(content, str) or not content.strip():
                raise RetrievalError(f"Chroma result {index} has empty document content")
            if not isinstance(metadata, dict):
                raise RetrievalError(f"Chroma result {index} has invalid metadata")
            if not isinstance(distance, (int, float)) or not math.isfinite(float(distance)):
                raise RetrievalError(f"Chroma result {index} has an invalid distance")

            chunk_id = self._required_metadata_string(metadata, "chunk_id", index)
            document_name = self._required_metadata_string(metadata, "document_name", index)
            category = self._required_metadata_string(metadata, "category", index)
            if chunk_id != record_id:
                raise RetrievalError(
                    f"Chroma result {index} ID does not match its chunk_id metadata"
                )

            metadata_copy = dict(metadata)
            results.append(
                RetrievalResult(
                    document=Document(page_content=content, metadata=dict(metadata_copy)),
                    metadata=metadata_copy,
                    similarity_score=self._distance_to_similarity(float(distance)),
                    chunk_id=chunk_id,
                    document_name=document_name,
                    category=category,
                )
            )

        return results

    def _distance_to_similarity(self, distance: float) -> float:
        if self._distance_metric in {"cosine", "ip"}:
            return 1.0 - distance
        return 1.0 / (1.0 + max(distance, 0.0))

    @staticmethod
    def _first_result_row(raw_result: Mapping[str, Any], field: str) -> list[Any]:
        value = raw_result.get(field)
        if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], list):
            raise RetrievalError(f"Chroma returned an invalid {field!r} result field")
        return value[0]

    @staticmethod
    def _required_metadata_string(metadata: dict[str, Any], key: str, index: int) -> str:
        value = metadata.get(key)
        if not isinstance(value, str) or not value:
            raise RetrievalError(
                f"Chroma result {index} is missing required metadata field {key!r}"
            )
        return value

    @staticmethod
    def _read_distance_metric(collection: Collection) -> str:
        configuration = collection.configuration
        index_configuration = configuration.get("hnsw") or configuration.get("spann") or {}
        metric = index_configuration.get("space", "l2")
        if metric not in _SUPPORTED_DISTANCE_METRICS:
            raise RetrievalConfigurationError(
                f"Unsupported Chroma distance metric: {metric!r}"
            )
        return metric

    @staticmethod
    def _build_where_filter(
        filters: Mapping[str, MetadataValue] | None,
    ) -> dict[str, Any] | None:
        if filters is None:
            return None
        if not isinstance(filters, Mapping):
            raise TypeError("filters must be a mapping")
        if not filters:
            return None

        conditions: list[dict[str, Any]] = []
        for key, value in filters.items():
            if key not in SUPPORTED_FILTER_FIELDS:
                supported = ", ".join(sorted(SUPPORTED_FILTER_FIELDS))
                raise RetrievalValidationError(
                    f"Unsupported metadata filter {key!r}; supported filters: {supported}"
                )
            if value is None or not isinstance(value, _FILTER_VALUE_TYPES):
                raise RetrievalValidationError(
                    f"Filter {key!r} must have a string, integer, float, or Boolean value"
                )
            conditions.append({key: {"$eq": value}})

        return conditions[0] if len(conditions) == 1 else {"$and": conditions}

    @staticmethod
    def _validate_query(query: str) -> str:
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        normalized = query.strip()
        if not normalized:
            raise RetrievalValidationError("query cannot be empty")
        return normalized

    @staticmethod
    def _validate_query_embedding(embedding: list[float]) -> None:
        if not isinstance(embedding, list) or not embedding:
            raise RetrievalError("Embedder returned an empty or invalid query embedding")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in embedding
        ):
            raise RetrievalError("Embedder returned non-numeric or non-finite values")

    @staticmethod
    def _validate_embedder(embedder: DocumentEmbedder) -> None:
        if not isinstance(embedder, DocumentEmbedder):
            raise RetrievalConfigurationError(
                "embedder must be an initialized DocumentEmbedder instance"
            )

    @staticmethod
    def _validate_top_k(top_k: int) -> None:
        if isinstance(top_k, bool) or not isinstance(top_k, int):
            raise TypeError("top_k must be an integer")
        if top_k <= 0:
            raise RetrievalValidationError("top_k must be greater than zero")

    @staticmethod
    def _validate_score_threshold(score_threshold: float | None) -> None:
        if score_threshold is None:
            return
        if isinstance(score_threshold, bool) or not isinstance(score_threshold, (int, float)):
            raise TypeError("score_threshold must be a number or None")
        if not math.isfinite(float(score_threshold)):
            raise RetrievalValidationError("score_threshold must be finite")
