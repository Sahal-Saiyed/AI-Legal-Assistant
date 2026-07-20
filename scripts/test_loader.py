"""Manual smoke test for the knowledge-base document loader."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.loaders import KnowledgeBaseDocumentLoader  # noqa: E402


def main() -> None:
    """Load the knowledge base and print a compact document summary."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    loader = KnowledgeBaseDocumentLoader(PROJECT_ROOT / "knowledge_base")
    documents = loader.load()

    print(f"Total documents loaded: {len(documents)}")
    for document in documents:
        metadata = document.metadata
        print()
        print(f"Document Name: {metadata['document_name']}")
        print(f"Category: {metadata['category']}")
        print(f"File Type: {metadata['file_type']}")
        print(f"Character Count: {len(document.page_content)}")


if __name__ == "__main__":
    main()

