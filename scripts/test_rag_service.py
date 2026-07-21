"""End-to-end smoke test for the reusable RAG orchestration service."""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services import RAGService  # noqa: E402

DEFAULT_QUESTION = "How do I file an FIR?"


def main() -> None:
    """Ask one question and print the structured service response."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION
    service = RAGService.from_env()
    response = service.ask(question)

    print("=" * 60)
    print("RAG SERVICE TEST")
    print("=" * 60)
    for field_name, value in asdict(response).items():
        print(f"{field_name}: {value}")
    print("Validation: PASSED")


if __name__ == "__main__":
    main()
