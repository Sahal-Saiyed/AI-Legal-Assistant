"""End-to-end smoke test for the E5 embedding module."""

from __future__ import annotations

import logging
import math
import sys
from pathlib import Path
from statistics import fmean
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.chunkers import RecursiveDocumentChunker  # noqa: E402
from backend.app.rag.embeddings import E5Embedder  # noqa: E402
from backend.app.rag.loaders import KnowledgeBaseDocumentLoader  # noqa: E402

SAMPLE_VECTOR_COUNT = 3
NORMALIZATION_TOLERANCE = 1e-5


def _vector_norm(vector: list[float]) -> float:
    return math.sqrt(math.fsum(value * value for value in vector))


def _validate_embeddings(embeddings: list[list[float]], expected_count: int) -> int:
    """Validate positional count, dimensions, finite values, and normalization."""
    if len(embeddings) != expected_count:
        raise AssertionError(
            f"Expected {expected_count} embeddings, received {len(embeddings)}"
        )
    if not embeddings:
        raise AssertionError("No embeddings were generated")

    dimension = len(embeddings[0])
    if dimension == 0:
        raise AssertionError("Embedding dimension cannot be zero")

    for index, vector in enumerate(embeddings):
        if len(vector) != dimension:
            raise AssertionError(f"Inconsistent embedding dimension at index {index}")
        if not all(math.isfinite(value) for value in vector):
            raise AssertionError(f"Non-finite embedding value at index {index}")
        if not math.isclose(
            _vector_norm(vector),
            1.0,
            rel_tol=NORMALIZATION_TOLERANCE,
            abs_tol=NORMALIZATION_TOLERANCE,
        ):
            raise AssertionError(f"Embedding at index {index} is not normalized")

    return dimension


def _print_vector_statistics(embeddings: list[list[float]]) -> None:
    for index, vector in enumerate(embeddings[:SAMPLE_VECTOR_COUNT]):
        print(
            f"Sample {index}: min={min(vector):.6f}, max={max(vector):.6f}, "
            f"mean={fmean(vector):.6f}, L2 norm={_vector_norm(vector):.6f}"
        )


def main() -> None:
    """Load, chunk, embed, validate, and report compact metrics."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    loader = KnowledgeBaseDocumentLoader(PROJECT_ROOT / "knowledge_base")
    source_documents = loader.load()
    chunker = RecursiveDocumentChunker()
    chunks = chunker.split_documents(source_documents)

    embedder = E5Embedder(batch_size=32)
    started_at = perf_counter()
    embeddings = embedder.embed_documents(chunks)
    processing_time = perf_counter() - started_at

    dimension = _validate_embeddings(embeddings, expected_count=len(chunks))
    query_embedding = embedder.embed_query("What are a consumer's legal rights?")
    _validate_embeddings([query_embedding], expected_count=1)

    print(f"Number of chunks processed: {len(chunks)}")
    print(f"Embedding dimension: {dimension}")
    print(f"Embedding shape: ({len(embeddings)}, {dimension})")
    print(f"Processing time: {processing_time:.2f} seconds")
    _print_vector_statistics(embeddings)
    print("Validation: PASSED")


if __name__ == "__main__":
    main()
