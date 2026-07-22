"""End-to-end smoke test for persistent Chroma vector storage."""

from __future__ import annotations

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
from backend.app.rag.vectorstore import ChromaVectorStore  # noqa: E402

TEST_COLLECTION_NAME = "legal_assistant"


def main() -> None:
    """Run the completed ingestion stages and validate Chroma persistence."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    loader = KnowledgeBaseDocumentLoader(PROJECT_ROOT / "knowledge_base")
    source_documents = loader.load()

    chunker = RecursiveDocumentChunker()
    chunks = chunker.split_documents(source_documents)

    embedder = E5Embedder(batch_size=32)
    embedding_values = embedder.embed_documents(chunks)
    embeddings = np.asarray(embedding_values, dtype=np.float32)

    store = ChromaVectorStore(
        database_path=PROJECT_ROOT / "vector_dbs" / "chroma",
        collection_name=TEST_COLLECTION_NAME,
    )
    store.reset_collection()
    store.add_documents(chunks, embeddings)
    stored_count = store.count_documents()

    if len(embeddings) != len(chunks):
        raise AssertionError("Embedding count does not match chunk count")
    if stored_count != len(chunks):
        raise AssertionError("Collection count does not match chunk count")

    print("=========================================")
    print("VECTOR STORE TEST")
    print("=========================================")
    print(f"Documents Loaded : {len(source_documents)}")
    print(f"Chunks Created : {len(chunks)}")
    print(f"Embeddings Generated : {len(embeddings)}")
    print(f"Collection : {store.collection_name}")
    print(f"Vectors Stored : {stored_count}")
    print(f"Collection Count : {store.count_documents()}")
    print(f"Database Path : {store.database_path}")
    print("Validation : PASSED")


if __name__ == "__main__":
    main()
