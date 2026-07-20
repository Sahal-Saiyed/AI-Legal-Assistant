"""Manual smoke test and validation for the document chunker."""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.chunkers import RecursiveDocumentChunker  # noqa: E402
from backend.app.rag.loaders import KnowledgeBaseDocumentLoader  # noqa: E402

PREVIEW_CHUNK_COUNT = 5


def _source_key(document: Document) -> str:
    """Return the loader's stable per-source key."""
    relative_path = document.metadata.get("relative_path")
    if not isinstance(relative_path, str) or not relative_path:
        raise AssertionError("Source document is missing relative_path metadata")
    return relative_path


def _validate_chunks(
    source_documents: list[Document],
    chunks: list[Document],
    chunker: RecursiveDocumentChunker,
) -> None:
    """Validate content, metadata, indexes, IDs, and active configuration."""
    if chunker.chunk_overlap != 200:
        raise AssertionError("Configured chunk overlap was not applied")

    sources_by_key = {_source_key(document): document for document in source_documents}
    chunks_by_source: dict[str, list[Document]] = defaultdict(list)
    chunk_ids: set[str] = set()

    for chunk in chunks:
        if not chunk.page_content.strip():
            raise AssertionError("Empty chunk found")

        source_key = _source_key(chunk)
        if source_key not in sources_by_key:
            raise AssertionError(f"Chunk has unknown source: {source_key}")

        source_metadata = sources_by_key[source_key].metadata
        for key, value in source_metadata.items():
            if chunk.metadata.get(key) != value:
                raise AssertionError(f"Metadata was not preserved for {source_key}: {key}")

        if chunk.metadata.get("chunk_size") != len(chunk.page_content):
            raise AssertionError(f"Incorrect chunk_size for {source_key}")

        chunk_id = chunk.metadata.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            raise AssertionError(f"Missing chunk_id for {source_key}")
        if chunk_id in chunk_ids:
            raise AssertionError(f"Duplicate chunk_id found: {chunk_id}")
        chunk_ids.add(chunk_id)
        chunks_by_source[source_key].append(chunk)

    for source_key, source_chunks in chunks_by_source.items():
        ordered_chunks = sorted(source_chunks, key=lambda chunk: chunk.metadata["chunk_index"])
        expected_indexes = list(range(len(ordered_chunks)))
        actual_indexes = [chunk.metadata.get("chunk_index") for chunk in ordered_chunks]
        if actual_indexes != expected_indexes:
            raise AssertionError(f"Invalid chunk indexes for {source_key}")
        if any(chunk.metadata.get("chunk_count") != len(ordered_chunks) for chunk in ordered_chunks):
            raise AssertionError(f"Incorrect chunk_count for {source_key}")

    repeated_chunks = chunker.split_documents(source_documents)
    repeated_ids = [chunk.metadata["chunk_id"] for chunk in repeated_chunks]
    if repeated_ids != [chunk.metadata["chunk_id"] for chunk in chunks]:
        raise AssertionError("Chunk IDs are not deterministic")


def _print_summary(source_documents: list[Document], chunks: list[Document]) -> None:
    chunks_by_source: dict[str, list[Document]] = defaultdict(list)
    for chunk in chunks:
        chunks_by_source[_source_key(chunk)].append(chunk)

    total_documents = len(source_documents)
    average = len(chunks) / total_documents if total_documents else 0.0
    print(f"Total source documents: {total_documents}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Average chunks per document: {average:.2f}")

    for document in source_documents:
        source_key = _source_key(document)
        print()
        print(f"Document: {source_key}")
        print(f"Original length: {len(document.page_content)}")
        print(f"Number of chunks: {len(chunks_by_source[source_key])}")

    print(f"\nFirst {min(PREVIEW_CHUNK_COUNT, len(chunks))} chunks:")
    for chunk in chunks[:PREVIEW_CHUNK_COUNT]:
        print()
        print(f"Chunk Index: {chunk.metadata['chunk_index']}")
        print(f"Chunk Size: {len(chunk.page_content)}")
        print(f"Chunk Metadata: {_format_metadata(chunk.metadata)}")


def _format_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return metadata unchanged while giving the print operation a typed boundary."""
    return dict(metadata)


def main() -> None:
    """Load, chunk, validate, and print a compact summary."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    loader = KnowledgeBaseDocumentLoader(PROJECT_ROOT / "knowledge_base")
    source_documents = loader.load()
    chunker = RecursiveDocumentChunker(chunk_size=1000, chunk_overlap=200)
    chunks = chunker.split_documents(source_documents)

    _validate_chunks(source_documents, chunks, chunker)
    _print_summary(source_documents, chunks)
    print("\nValidation: PASSED")
    print(chunks[0].metadata)


if __name__ == "__main__":
    main()
