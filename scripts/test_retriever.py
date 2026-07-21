"""Manual smoke test for semantic retrieval from the existing Chroma collection."""

from __future__ import annotations

import logging
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.embeddings import E5Embedder  # noqa: E402
from backend.app.rag.retrieval import ChromaRetriever, RetrievalResult  # noqa: E402

COLLECTION_NAME = "legal_assistant"
TOP_K = 5
CONTENT_PREVIEW_LENGTH = 300
TEST_QUERIES = (
    "What are my consumer rights if an online seller refuses a refund?",
    "Can an employer terminate me without notice?",
    "How do I file an FIR?",
    "What is domestic violence under Indian law?",
)


def _validate_results(results: list[RetrievalResult], top_k: int) -> None:
    if len(results) > top_k:
        raise AssertionError(f"Retriever returned more than top_k={top_k} results")
    if not results:
        raise AssertionError("Retriever returned no results")

    scores = [result.similarity_score for result in results]
    if any(not math.isfinite(score) for score in scores):
        raise AssertionError("Retriever returned a non-finite score")
    if scores != sorted(scores, reverse=True):
        raise AssertionError("Results are not sorted by descending similarity")

    for result in results:
        if not result.chunk_id or not result.category or not result.document_name:
            raise AssertionError("Result is missing required identifying metadata")
        if not result.document.page_content.strip():
            raise AssertionError("Result contains empty chunk content")
        if result.document.metadata != result.metadata:
            raise AssertionError("Document and result metadata do not match")


def _print_results(query: str, results: list[RetrievalResult]) -> None:
    print("=" * 50)
    print("QUERY")
    print("=" * 50)
    print(query)
    print(f"\nRetrieved: {len(results)} chunks")

    for index, result in enumerate(results, start=1):
        preview = " ".join(result.document.page_content.split())[:CONTENT_PREVIEW_LENGTH]
        print()
        print("=" * 50)
        print(f"RESULT {index}")
        print("=" * 50)
        print(f"Score: {result.similarity_score:.6f}")
        print(f"Chunk ID: {result.chunk_id}")
        print(f"Category: {result.category}")
        print(f"Document: {result.document_name}")
        print(f"Content Preview: {preview}")


def main() -> None:
    """Run realistic legal queries against the existing collection."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    embedder = E5Embedder()
    retriever = ChromaRetriever(
        embedder=embedder,
        collection_name=COLLECTION_NAME,
        top_k=TOP_K,
        database_path=PROJECT_ROOT / "vector_dbs" / "chroma",
    )

    print("RETRIEVER TEST")
    print(f"Collection: {retriever.collection_name}")

    for query in TEST_QUERIES:
        results = retriever.retrieve(query)
        _validate_results(results, TOP_K)
        _print_results(query, results)

    filtered_results = retriever.retrieve(
        "What are my consumer rights?",
        top_k=TOP_K,
        filters={"category": "consumer", "source": "official"},
    )
    _validate_results(filtered_results, TOP_K)
    if any(result.category != "consumer" for result in filtered_results):
        raise AssertionError("Category metadata filter was not applied")

    print("\nValidation: PASSED")


if __name__ == "__main__":
    main()
