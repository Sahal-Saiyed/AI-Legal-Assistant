"""Deterministic cleanup and consolidation of retrieved legal chunks."""

from __future__ import annotations

import logging
import math
import re
from collections import OrderedDict
from dataclasses import dataclass
from time import perf_counter
from typing import Final

from backend.app.rag.retrieval.base import RetrievalResult

from .base import PromptValidationError

logger = logging.getLogger(__name__)

DEFAULT_MINIMUM_OVERLAP_TOKENS: Final[int] = 5
_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"\S+")
_BOUNDARY_PUNCTUATION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\W+|\W+$")


@dataclass(frozen=True, slots=True)
class ProcessedContextChunk:
    """One optimized chunk with complete provenance back to retrieval results."""

    content: str
    document_name: str
    category: str
    source_identity: str
    original_results: tuple[RetrievalResult, ...]


@dataclass(frozen=True, slots=True)
class ContextProcessingResult:
    """Processed chunks and auditable optimization statistics."""

    chunks: tuple[ProcessedContextChunk, ...]
    original_chunk_count: int
    duplicate_chunks_removed: int
    chunks_merged: int
    final_chunk_count: int
    original_context_size: int
    optimized_context_size: int
    characters_saved: int


@dataclass(slots=True)
class _ChunkCandidate:
    """Mutable internal representation used while consolidating provenance."""

    content: str
    document_name: str
    category: str
    source_identity: str
    first_retrieval_rank: int
    chunk_index: int | None
    original_results: list[RetrievalResult]


class ContextProcessor:
    """Remove redundant retrieval text without crossing source boundaries."""

    def __init__(
        self,
        minimum_overlap_tokens: int = DEFAULT_MINIMUM_OVERLAP_TOKENS,
    ) -> None:
        if isinstance(minimum_overlap_tokens, bool) or not isinstance(
            minimum_overlap_tokens, int
        ):
            raise TypeError("minimum_overlap_tokens must be an integer")
        if minimum_overlap_tokens <= 0:
            raise PromptValidationError("minimum_overlap_tokens must be greater than zero")
        self._minimum_overlap_tokens = minimum_overlap_tokens

    @property
    def minimum_overlap_tokens(self) -> int:
        """Minimum boundary-token match required before merging chunks."""
        return self._minimum_overlap_tokens

    def process(
        self,
        retrieved_documents: list[RetrievalResult],
    ) -> ContextProcessingResult:
        """Deduplicate and merge retrieved chunks while retaining provenance."""
        started_at = perf_counter()
        self._validate_retrieved_documents(retrieved_documents)

        original_context_size = sum(
            len(result.document.page_content.strip()) for result in retrieved_documents
        )
        candidates, duplicate_count = self._remove_duplicates(retrieved_documents)
        processed_chunks, merge_count = self._merge_by_source(candidates)
        optimized_context_size = sum(len(chunk.content) for chunk in processed_chunks)
        characters_saved = original_context_size - optimized_context_size

        result = ContextProcessingResult(
            chunks=tuple(processed_chunks),
            original_chunk_count=len(retrieved_documents),
            duplicate_chunks_removed=duplicate_count,
            chunks_merged=merge_count,
            final_chunk_count=len(processed_chunks),
            original_context_size=original_context_size,
            optimized_context_size=optimized_context_size,
            characters_saved=characters_saved,
        )
        logger.info(
            "Processed retrieval context | original_chunks=%d | duplicates_removed=%d | "
            "chunks_merged=%d | final_chunks=%d | original_size=%d | "
            "optimized_size=%d | characters_saved=%d | duration=%.6fs",
            result.original_chunk_count,
            result.duplicate_chunks_removed,
            result.chunks_merged,
            result.final_chunk_count,
            result.original_context_size,
            result.optimized_context_size,
            result.characters_saved,
            perf_counter() - started_at,
        )
        return result

    def _remove_duplicates(
        self,
        retrieved_documents: list[RetrievalResult],
    ) -> tuple[list[_ChunkCandidate], int]:
        candidates: list[_ChunkCandidate] = []
        seen: dict[tuple[str, str], _ChunkCandidate] = {}
        duplicate_count = 0

        for rank, result in enumerate(retrieved_documents):
            content = result.document.page_content.strip()
            source_identity = self._source_identity(result)
            duplicate_key = (source_identity, content)
            existing = seen.get(duplicate_key)
            if existing is not None:
                existing.original_results.append(result)
                duplicate_count += 1
                continue

            candidate = _ChunkCandidate(
                content=content,
                document_name=result.document_name.strip(),
                category=result.category.strip(),
                source_identity=source_identity,
                first_retrieval_rank=rank,
                chunk_index=self._chunk_index(result),
                original_results=[result],
            )
            seen[duplicate_key] = candidate
            candidates.append(candidate)

        return candidates, duplicate_count

    def _merge_by_source(
        self,
        candidates: list[_ChunkCandidate],
    ) -> tuple[list[ProcessedContextChunk], int]:
        grouped: OrderedDict[str, list[_ChunkCandidate]] = OrderedDict()
        for candidate in candidates:
            grouped.setdefault(candidate.source_identity, []).append(candidate)

        processed_chunks: list[ProcessedContextChunk] = []
        merge_count = 0
        for source_candidates in grouped.values():
            ordered_candidates = self._order_source_candidates(source_candidates)
            merged_candidates: list[_ChunkCandidate] = []

            for candidate in ordered_candidates:
                if merged_candidates:
                    previous = merged_candidates[-1]
                    merged_content = self._merge_overlapping_content(
                        previous.content,
                        candidate.content,
                    )
                    if merged_content is not None:
                        previous.content = merged_content
                        previous.original_results.extend(candidate.original_results)
                        merge_count += 1
                        continue
                merged_candidates.append(candidate)

            processed_chunks.extend(
                ProcessedContextChunk(
                    content=candidate.content,
                    document_name=candidate.document_name,
                    category=candidate.category,
                    source_identity=candidate.source_identity,
                    original_results=tuple(candidate.original_results),
                )
                for candidate in merged_candidates
            )

        return processed_chunks, merge_count

    @staticmethod
    def _order_source_candidates(
        candidates: list[_ChunkCandidate],
    ) -> list[_ChunkCandidate]:
        if all(candidate.chunk_index is not None for candidate in candidates):
            return sorted(
                candidates,
                key=lambda candidate: (
                    candidate.chunk_index,
                    candidate.first_retrieval_rank,
                ),
            )
        return sorted(candidates, key=lambda candidate: candidate.first_retrieval_rank)

    def _merge_overlapping_content(self, first: str, second: str) -> str | None:
        first_tokens = self._tokens_with_spans(first)
        second_tokens = self._tokens_with_spans(second)
        maximum_overlap = min(len(first_tokens), len(second_tokens))

        for overlap_size in range(maximum_overlap, self._minimum_overlap_tokens - 1, -1):
            first_boundary = [token[0] for token in first_tokens[-overlap_size:]]
            second_boundary = [token[0] for token in second_tokens[:overlap_size]]
            if first_boundary != second_boundary:
                continue

            overlap_end = second_tokens[overlap_size - 1][2]
            remainder = second[overlap_end:]
            if not remainder:
                return first
            if remainder[0].isspace() or self._starts_with_punctuation(remainder):
                return first.rstrip() + remainder
            return f"{first.rstrip()} {remainder.lstrip()}"

        return None

    @staticmethod
    def _tokens_with_spans(content: str) -> list[tuple[str, int, int]]:
        tokens: list[tuple[str, int, int]] = []
        for match in _TOKEN_PATTERN.finditer(content):
            normalized = _BOUNDARY_PUNCTUATION_PATTERN.sub("", match.group()).casefold()
            if not normalized:
                normalized = match.group().casefold()
            tokens.append((normalized, match.start(), match.end()))
        return tokens

    @staticmethod
    def _starts_with_punctuation(value: str) -> bool:
        stripped = value.lstrip()
        return bool(stripped and not stripped[0].isalnum())

    @staticmethod
    def _source_identity(result: RetrievalResult) -> str:
        relative_path = result.metadata.get("relative_path")
        if isinstance(relative_path, str) and relative_path.strip():
            return f"relative_path:{relative_path.strip()}"
        source = result.metadata.get("source", "")
        return "fallback:{category}|{source}|{document_name}".format(
            category=result.category.strip(),
            source=str(source).strip(),
            document_name=result.document_name.strip(),
        )

    @staticmethod
    def _chunk_index(result: RetrievalResult) -> int | None:
        value = result.metadata.get("chunk_index")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        return value

    @staticmethod
    def _validate_retrieved_documents(
        retrieved_documents: list[RetrievalResult],
    ) -> None:
        if not isinstance(retrieved_documents, list):
            raise TypeError("retrieved_documents must be a list of RetrievalResult objects")
        if not retrieved_documents:
            raise PromptValidationError("retrieved_documents cannot be empty")

        for index, result in enumerate(retrieved_documents):
            if not isinstance(result, RetrievalResult):
                raise TypeError(f"retrieved_documents[{index}] must be a RetrievalResult")
            if not result.document.page_content.strip():
                raise PromptValidationError(
                    f"retrieved_documents[{index}] contains empty content"
                )
            if not result.document_name.strip() or not result.category.strip():
                raise PromptValidationError(
                    f"retrieved_documents[{index}] lacks document identity metadata"
                )
            if not math.isfinite(result.similarity_score):
                raise PromptValidationError(
                    f"retrieved_documents[{index}] has a non-finite similarity score"
                )
