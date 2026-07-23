"""Rebuild the complete Chroma collection from knowledge documents only."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

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

    chunks = RecursiveDocumentChunker().split_documents(documents)
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


if __name__ == "__main__":
    main()
