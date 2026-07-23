"""Rebuild the complete Chroma collection from knowledge documents only."""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from langchain_core.documents import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.chunkers import RecursiveDocumentChunker  # noqa: E402
from backend.app.rag.embeddings import E5Embedder  # noqa: E402
from backend.app.rag.loaders import KnowledgeBaseDocumentLoader  # noqa: E402
from backend.app.rag.vectorstore import (  # noqa: E402
    DEFAULT_COLLECTION_NAME,
    ChromaVectorStore,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Destructively rebuild Chroma from legal knowledge while excluding "
            "knowledge_base/templates."
        )
    )
    parser.add_argument(
        "--knowledge-base",
        type=Path,
        default=PROJECT_ROOT / "knowledge_base",
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=PROJECT_ROOT / "vector_dbs" / "chroma",
    )
    parser.add_argument("--collection", default=DEFAULT_COLLECTION_NAME)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm replacement of the existing collection.",
    )
    return parser.parse_args()


def validate_unique_source_documents(documents: list[Document]) -> None:
    """Reject byte-equivalent extracted documents before destructive operations."""
    documents_by_content: dict[str, list[Document]] = defaultdict(list)
    for document in documents:
        content_hash = hashlib.sha256(
            document.page_content.encode("utf-8")
        ).hexdigest()
        documents_by_content[content_hash].append(document)

    duplicate_groups = [
        group for group in documents_by_content.values() if len(group) > 1
    ]
    if not duplicate_groups:
        return

    details: list[str] = []
    for group in duplicate_groups:
        paths = sorted(
            str(document.metadata.get("relative_path", "<unknown>"))
            for document in group
        )
        details.append("\n".join(f"  - {path}" for path in paths))
    formatted_groups = "\n\n".join(details)
    raise RuntimeError(
        "Duplicate source documents were found. Identical source content produces "
        "identical deterministic chunk IDs. Keep one canonical copy of each document "
        "and remove the duplicates before rebuilding:\n\n"
        f"{formatted_groups}\n\n"
        "The existing Chroma collection has not been modified."
    )


def validate_unique_chunk_ids(chunks: list[Document]) -> None:
    """Catch any remaining deterministic ID collision before resetting Chroma."""
    chunks_by_id: dict[str, list[Document]] = defaultdict(list)
    for chunk in chunks:
        chunks_by_id[str(chunk.metadata.get("chunk_id", ""))].append(chunk)
    duplicates = {
        chunk_id: values
        for chunk_id, values in chunks_by_id.items()
        if not chunk_id or len(values) > 1
    }
    if not duplicates:
        return

    preview: list[str] = []
    for chunk_id, values in list(duplicates.items())[:5]:
        sources = ", ".join(
            str(value.metadata.get("relative_path", "<unknown>"))
            for value in values
        )
        preview.append(f"  - {chunk_id or '<missing>'}: {sources}")
    raise RuntimeError(
        "Duplicate or missing chunk IDs were detected before rebuilding Chroma:\n"
        + "\n".join(preview)
        + "\nThe existing Chroma collection has not been modified."
    )


def main() -> None:
    args = parse_args()
    if not args.yes:
        raise SystemExit(
            "Refusing to replace the Chroma collection without explicit --yes."
        )
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be greater than zero")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    documents = KnowledgeBaseDocumentLoader(args.knowledge_base).load()
    template_documents = [
        document
        for document in documents
        if str(document.metadata.get("category", "")).casefold() == "templates"
        or str(document.metadata.get("relative_path", ""))
        .replace("\\", "/")
        .casefold()
        .startswith("templates/")
    ]
    if template_documents:
        raise RuntimeError(
            "Template isolation failed; refusing to rebuild the vector collection"
        )
    if not documents:
        raise RuntimeError("No legal knowledge documents were loaded")

    validate_unique_source_documents(documents)
    chunks = RecursiveDocumentChunker().split_documents(documents)
    validate_unique_chunk_ids(chunks)
    embeddings = np.asarray(
        E5Embedder(batch_size=args.batch_size).embed_documents(chunks),
        dtype=np.float32,
    )
    store = ChromaVectorStore(
        database_path=args.database_path,
        collection_name=args.collection,
    )
    store.reset_collection()
    store.add_documents(chunks, embeddings)

    print("=========================================")
    print("CHROMA REBUILD COMPLETE")
    print("=========================================")
    print(f"Knowledge documents : {len(documents)}")
    print(f"Template documents  : {len(template_documents)}")
    print(f"Chunks stored       : {store.count_documents()}")
    print(f"Collection          : {store.collection_name}")
    print(f"Database path       : {store.database_path}")
    print("Chunks by category  :")
    chunks_by_category = Counter(
        str(chunk.metadata.get("category", "<unknown>")) for chunk in chunks
    )
    for category, count in sorted(chunks_by_category.items()):
        print(f"  {category:<24} {count}")


if __name__ == "__main__":
    main()
