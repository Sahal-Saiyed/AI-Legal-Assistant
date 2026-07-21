"""End-to-end smoke test for Gemini generation over the legal RAG pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.llm import GeminiClient, LLMConfig, LLMResponse  # noqa: E402
from backend.app.rag.embeddings import E5Embedder  # noqa: E402
from backend.app.rag.prompts import ContextProcessor, LegalPromptBuilder  # noqa: E402
from backend.app.rag.retrieval import ChromaRetriever  # noqa: E402

DEFAULT_QUESTION = "How do I file an FIR?"
TOP_K = 5


def _validate_response(response: LLMResponse, expected_model: str) -> None:
    """Validate the LLM response."""

    if not response.answer.strip():
        raise AssertionError("Gemini returned an empty answer")

    if response.model_name != expected_model:
        raise AssertionError("Response model does not match configured model")

    if response.generation_time < 0:
        raise AssertionError("Generation duration cannot be negative")

    if (
        response.input_token_count is not None
        and response.input_token_count < 0
    ):
        raise AssertionError("Input token count cannot be negative")

    if (
        response.output_token_count is not None
        and response.output_token_count < 0
    ):
        raise AssertionError("Output token count cannot be negative")


def _display_optional(value: int | str | None) -> str:
    """Display optional values."""
    return "Unavailable" if value is None else str(value)


def main() -> None:
    """Run the complete RAG pipeline."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    question = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else DEFAULT_QUESTION
    )

    config = LLMConfig.from_env()

    embedder = E5Embedder()

    retriever = ChromaRetriever(
        embedder=embedder,
        collection_name="legal_assistant",
        top_k=TOP_K,
        database_path=PROJECT_ROOT / "vector_dbs" / "chroma",
    )

    retrieved_results = retriever.retrieve(question)

    processed_context = ContextProcessor().process(retrieved_results)

    prompt = LegalPromptBuilder().build(
        question,
        processed_context,
    )

    print("=" * 60)
    print("LLM TEST")
    print("=" * 60)

    print(f"\nQuestion:\n{question}")

    print("\nRetrieved Documents")
    print("-" * 60)

    for index, chunk in enumerate(retrieved_results, start=1):
        metadata = chunk.metadata

        source = metadata.get("source_document", "Unknown")
        score = getattr(chunk, "similarity_score", None)

        if score is not None:
            print(f"{index}. {source} ({score:.3f})")
        else:
            print(f"{index}. {source}")

    print("\nUnique Source Documents")
    print("-" * 60)

    for source in prompt.source_documents:
        print(f"• {source}")

    print(f"\nUsing Model:\n{config.model}")

    print("\nGenerating...")

    with GeminiClient(config) as client:

        if not client.health_check():
            raise AssertionError("Gemini health check failed")

        response = client.generate(
            prompt.system_prompt,
            prompt.user_prompt,
        )

    _validate_response(response, config.model)

    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(response.answer)

    print("\n" + "=" * 60)
    print("STATISTICS")
    print("=" * 60)

    print(f"Generation Time : {response.generation_time:.2f} sec")
    print(f"Model           : {response.model_name}")
    print(f"Prompt Tokens   : {_display_optional(response.input_token_count)}")
    print(f"Completion Tokens: {_display_optional(response.output_token_count)}")
    print(f"Finish Reason   : {_display_optional(response.finish_reason)}")

    print("\nValidation: PASSED")


if __name__ == "__main__":
    main()