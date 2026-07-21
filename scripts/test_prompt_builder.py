"""End-to-end and deterministic tests for context processing and prompt building."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from langchain_core.documents import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.embeddings import E5Embedder  # noqa: E402
from backend.app.rag.prompts import (  # noqa: E402
    ContextProcessingResult,
    ContextProcessor,
    LegalPrompt,
    LegalPromptBuilder,
)
from backend.app.rag.retrieval import ChromaRetriever, RetrievalResult  # noqa: E402

QUESTION = "How do I file an FIR?"
TOP_K = 5


def _make_result(
    content: str,
    chunk_id: str,
    chunk_index: int,
    document_name: str = "FIR Guide",
) -> RetrievalResult:
    metadata = {
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "document_name": document_name,
        "category": "police_legal_aid",
        "source": "official",
        "relative_path": f"police_legal_aid/official/{document_name}.pdf",
    }
    return RetrievalResult(
        document=Document(page_content=content, metadata=dict(metadata)),
        metadata=metadata,
        similarity_score=0.9 - (chunk_index * 0.01),
        chunk_id=chunk_id,
        document_name=document_name,
        category="police_legal_aid",
    )


def _validate_prompt(
    question: str,
    prompt: LegalPrompt,
    processed: ContextProcessingResult,
    builder: LegalPromptBuilder,
) -> None:
    if not all(
        (prompt.system_prompt, prompt.user_prompt, prompt.formatted_context, prompt.question)
    ):
        raise AssertionError("Prompt contains an empty required field")
    if prompt.question != question:
        raise AssertionError("Prompt did not preserve the question")
    if len(prompt.formatted_context) > builder.maximum_context_characters:
        raise AssertionError("Formatted context exceeds its character limit")
    if prompt.formatted_context.count("Document:\n") > builder.maximum_context_documents:
        raise AssertionError("Formatted context exceeds its document limit")
    if question not in prompt.user_prompt or prompt.formatted_context not in prompt.user_prompt:
        raise AssertionError("User prompt is missing the question or context")
    if "Similarity:" in prompt.system_prompt + prompt.formatted_context + prompt.user_prompt:
        raise AssertionError("Similarity score leaked into the LLM-facing prompt")
    if processed.characters_saved != (
        processed.original_context_size - processed.optimized_context_size
    ):
        raise AssertionError("Context-processing size metrics are inconsistent")
    if len(prompt.source_documents) != len(set(prompt.source_documents)):
        raise AssertionError("Source document names are not unique")
    for source_document in prompt.source_documents:
        if prompt.user_prompt.count(f"• {source_document}") != 1:
            raise AssertionError("Available source list is missing a unique document name")
    required_citation_instructions = (
        "Never use parenthetical source citations",
        'exactly two final sections in this order: "Sources" and "Disclaimer"',
        "Include each document actually relied upon exactly once",
    )
    if any(instruction not in prompt.system_prompt for instruction in required_citation_instructions):
        raise AssertionError("System prompt is missing citation-format instructions")
    if "This response is based solely on the supplied legal documents" not in (
        prompt.system_prompt
    ):
        raise AssertionError("Required disclaimer was not preserved")
    if 'write exactly "None" under "Sources"' not in prompt.system_prompt:
        raise AssertionError("Insufficient-context source behavior is not defined")


def _run_deterministic_processor_test(processor: ContextProcessor) -> None:
    first = "The complainant may approach the Superintendent of Police for assistance."
    second = (
        "the complainant may approach the Superintendent of Police for assistance. "
        "The complaint may subsequently be sent to the Magistrate."
    )
    retrieved = [
        _make_result(first, "test-1", 0),
        _make_result(first, "test-duplicate", 0),
        _make_result(second, "test-2", 1),
        _make_result("A separate BNSS source remains separate.", "test-3", 0, "BNSS"),
    ]
    processed = processor.process(retrieved)
    repeated = processor.process(retrieved)

    if processed != repeated:
        raise AssertionError("Context processing is not deterministic")
    if processed.duplicate_chunks_removed != 1 or processed.chunks_merged != 1:
        raise AssertionError("Duplicate removal or overlap merging was not demonstrated")
    if processed.final_chunk_count != 2:
        raise AssertionError("Unexpected deterministic final chunk count")
    if len(processed.chunks[0].original_results) != 3:
        raise AssertionError("Original metadata and scores were not retained as provenance")
    if processed.chunks[0].content.casefold().count(
        "the complainant may approach the superintendent of police for assistance"
    ) != 1:
        raise AssertionError("Overlapping content was repeated after merging")
    if processed.chunks[0].source_identity == processed.chunks[1].source_identity:
        raise AssertionError("Different source documents were mixed")


def _print_section(title: str, content: str) -> None:
    print("=" * 40)
    print(title)
    print("=" * 40)
    print(content)
    print()


def main() -> None:
    """Retrieve, optimize, build, print, and validate a legal prompt."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    processor = ContextProcessor()
    _run_deterministic_processor_test(processor)

    embedder = E5Embedder()
    retriever = ChromaRetriever(
        embedder=embedder,
        collection_name="legal_assistant",
        top_k=TOP_K,
        database_path=PROJECT_ROOT / "vector_dbs" / "chroma",
    )
    retrieved_results = retriever.retrieve(QUESTION)
    processed = processor.process(retrieved_results)

    builder = LegalPromptBuilder(
        maximum_context_documents=TOP_K,
        maximum_context_characters=10_000,
    )
    prompt = builder.build(QUESTION, processed)
    _validate_prompt(QUESTION, prompt, processed, builder)

    print("PROMPT BUILDER TEST\n")
    print(f"Original Chunks: {processed.original_chunk_count}")
    print(f"Duplicate Chunks Removed: {processed.duplicate_chunks_removed}")
    print(f"Merged Chunks: {processed.chunks_merged}")
    print(f"Final Chunks: {processed.final_chunk_count}")
    print(f"Original Context: {processed.original_context_size} chars")
    print(f"Optimized Context: {processed.optimized_context_size} chars")
    print(f"Characters Saved: {processed.characters_saved}\n")
    _print_section("QUESTION", prompt.question)
    _print_section("SYSTEM PROMPT", prompt.system_prompt)
    _print_section("FORMATTED CONTEXT", prompt.formatted_context)
    _print_section("USER PROMPT", prompt.user_prompt)
    _print_section("SOURCE DOCUMENTS", "\n".join(prompt.source_documents))
    print("Prompt Generated: SUCCESS")
    print("Validation: PASSED")


if __name__ == "__main__":
    main()
