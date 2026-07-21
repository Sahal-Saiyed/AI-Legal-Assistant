"""Production prompt builder for retrieved Indian-law material."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Final

from .base import (
    ContextLimitError,
    LegalPrompt,
    PromptBuilder,
    PromptValidationError,
)
from .context_processor import ContextProcessingResult, ProcessedContextChunk
from .templates import (
    CONTEXT_BLOCK_TEMPLATE,
    CONTEXT_SEPARATOR,
    LEGAL_SYSTEM_PROMPT,
    LEGAL_USER_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)

DEFAULT_MAXIMUM_CONTEXT_DOCUMENTS: Final[int] = 5
DEFAULT_MAXIMUM_CONTEXT_CHARACTERS: Final[int] = 10_000


class LegalPromptBuilder(PromptBuilder):
    """Build a bounded legal prompt from ranked retrieval results."""

    def __init__(
        self,
        maximum_context_documents: int = DEFAULT_MAXIMUM_CONTEXT_DOCUMENTS,
        maximum_context_characters: int = DEFAULT_MAXIMUM_CONTEXT_CHARACTERS,
    ) -> None:
        self._validate_positive_integer(
            maximum_context_documents,
            "maximum_context_documents",
        )
        self._validate_positive_integer(
            maximum_context_characters,
            "maximum_context_characters",
        )
        self._maximum_context_documents = maximum_context_documents
        self._maximum_context_characters = maximum_context_characters

    @property
    def maximum_context_documents(self) -> int:
        """Maximum number of retrieved chunks included in a prompt."""
        return self._maximum_context_documents

    @property
    def maximum_context_characters(self) -> int:
        """Maximum number of characters in the formatted context."""
        return self._maximum_context_characters

    def build(
        self,
        question: str,
        processed_context: ContextProcessingResult,
    ) -> LegalPrompt:
        """Validate, bound, and format retrieved evidence into one legal prompt."""
        started_at = perf_counter()
        normalized_question = self._validate_question(question)
        self._validate_processed_context(processed_context)

        formatted_context, selected_chunks = self._build_context(processed_context.chunks)
        source_documents = self._collect_source_documents(selected_chunks)
        user_prompt = LEGAL_USER_PROMPT_TEMPLATE.format(
            question=normalized_question,
            formatted_context=formatted_context,
            available_source_documents=self._format_available_sources(source_documents),
        )
        prompt = LegalPrompt(
            system_prompt=LEGAL_SYSTEM_PROMPT.strip(),
            user_prompt=user_prompt,
            formatted_context=formatted_context,
            question=normalized_question,
            source_documents=source_documents,
        )

        duration = perf_counter() - started_at
        total_prompt_size = len(prompt.system_prompt) + len(prompt.user_prompt)
        logger.info(
            "Built legal prompt | question_length=%d | retrieved_chunks=%d | "
            "processed_chunks=%d | context_size=%d | prompt_size=%d | "
            "source_documents=%d | duration=%.6fs",
            len(normalized_question),
            processed_context.original_chunk_count,
            processed_context.final_chunk_count,
            len(formatted_context),
            total_prompt_size,
            len(source_documents),
            duration,
        )
        return prompt

    def _build_context(
        self,
        processed_chunks: tuple[ProcessedContextChunk, ...],
    ) -> tuple[str, list[ProcessedContextChunk]]:
        selected_chunks: list[ProcessedContextChunk] = []
        context_blocks: list[str] = []
        current_size = 0

        for chunk in processed_chunks[: self._maximum_context_documents]:
            block = CONTEXT_BLOCK_TEMPLATE.format(
                separator=CONTEXT_SEPARATOR,
                document_name=chunk.document_name,
                category=chunk.category,
                content=chunk.content,
            )
            joining_size = 2 if context_blocks else 0
            proposed_size = current_size + joining_size + len(block)
            if proposed_size > self._maximum_context_characters:
                break

            context_blocks.append(block)
            selected_chunks.append(chunk)
            current_size = proposed_size

        if not context_blocks:
            raise ContextLimitError(
                "maximum_context_characters is too small to fit the highest-ranked "
                "complete retrieved chunk"
            )

        return "\n\n".join(context_blocks), selected_chunks

    @staticmethod
    def _collect_source_documents(
        selected_chunks: list[ProcessedContextChunk],
    ) -> tuple[str, ...]:
        return tuple(dict.fromkeys(chunk.document_name for chunk in selected_chunks))

    @staticmethod
    def _format_available_sources(source_documents: tuple[str, ...]) -> str:
        return "\n".join(f"• {document_name}" for document_name in source_documents)

    @staticmethod
    def _validate_question(question: str) -> str:
        if not isinstance(question, str):
            raise TypeError("question must be a string")
        normalized = question.strip()
        if not normalized:
            raise PromptValidationError("question cannot be empty")
        return normalized

    @staticmethod
    def _validate_processed_context(
        processed_context: ContextProcessingResult,
    ) -> None:
        if not isinstance(processed_context, ContextProcessingResult):
            raise TypeError("processed_context must be a ContextProcessingResult")
        if not processed_context.chunks:
            raise PromptValidationError("processed_context cannot be empty")

    @staticmethod
    def _validate_positive_integer(value: int, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if value <= 0:
            raise PromptValidationError(f"{name} must be greater than zero")
