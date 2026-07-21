"""Application service that orchestrates the legal retrieval-augmented pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from time import perf_counter
from typing import TypeAlias

from backend.app.llm import BaseLLM, LLMError
from backend.app.rag.prompts import (
    ContextProcessor,
    LegalPromptBuilder,
    PromptBuilder,
    PromptBuilderError,
    PromptValidationError,
)
from backend.app.rag.retrieval import RetrievalError, Retriever

logger = logging.getLogger(__name__)

ManagedLLMFactory: TypeAlias = Callable[[], AbstractContextManager[BaseLLM]]


class RAGServiceError(RuntimeError):
    """Base exception for RAG orchestration failures."""


class RAGServiceConfigurationError(RAGServiceError):
    """Raised when service dependencies are invalid."""


class RAGValidationError(ValueError):
    """Raised when a RAG request is invalid."""


class RAGRetrievalError(RAGServiceError):
    """Raised when retrieval cannot complete."""


class RAGProcessingError(RAGServiceError):
    """Raised when retrieved evidence cannot be prepared for generation."""


class RAGGenerationError(RAGServiceError):
    """Raised when the language model cannot generate an answer."""


@dataclass(frozen=True, slots=True)
class RAGResponse:
    """Structured result returned by the complete legal RAG pipeline."""

    question: str
    answer: str
    source_documents: tuple[str, ...]
    generation_time: float
    model_name: str
    input_token_count: int | None
    output_token_count: int | None
    finish_reason: str | None
    retrieved_chunks_count: int
    processed_chunks_count: int


class RAGService:
    """Coordinate independent retrieval, context, prompt, and LLM components."""

    def __init__(
        self,
        retriever: Retriever,
        context_processor: ContextProcessor,
        prompt_builder: PromptBuilder,
        llm_factory: ManagedLLMFactory,
    ) -> None:
        if not isinstance(retriever, Retriever):
            raise RAGServiceConfigurationError("retriever must implement Retriever")
        if not isinstance(context_processor, ContextProcessor):
            raise RAGServiceConfigurationError(
                "context_processor must be a ContextProcessor"
            )
        if not isinstance(prompt_builder, PromptBuilder):
            raise RAGServiceConfigurationError("prompt_builder must implement PromptBuilder")
        if not callable(llm_factory):
            raise RAGServiceConfigurationError("llm_factory must be callable")

        self._retriever = retriever
        self._context_processor = context_processor
        self._prompt_builder = prompt_builder
        self._llm_factory = llm_factory

    @classmethod
    def from_env(cls) -> RAGService:
        """Build the current production pipeline from environment configuration."""
        from backend.app.llm import GeminiClient, LLMConfig
        from backend.app.rag.embeddings import E5Embedder
        from backend.app.rag.retrieval import ChromaRetriever

        llm_config = LLMConfig.from_env()
        retriever = ChromaRetriever(embedder=E5Embedder())
        return cls(
            retriever=retriever,
            context_processor=ContextProcessor(),
            prompt_builder=LegalPromptBuilder(),
            llm_factory=lambda: GeminiClient(llm_config),
        )

    def ask(self, question: str) -> RAGResponse:
        """Run one validated question through the complete RAG pipeline."""
        normalized_question = self._validate_question(question)
        pipeline_started_at = perf_counter()
        logger.info("Received RAG question: %r", normalized_question)

        retrieval_started_at = perf_counter()
        try:
            retrieved_results = self._retriever.retrieve(normalized_question)
        except RetrievalError as exc:
            logger.exception("RAG retrieval failed")
            raise RAGRetrievalError("Failed to retrieve legal context") from exc
        except Exception as exc:
            logger.exception("Unexpected retrieval failure")
            raise RAGRetrievalError("Unexpected failure while retrieving legal context") from exc

        retrieval_duration = perf_counter() - retrieval_started_at
        logger.info(
            "RAG retrieval completed | duration=%.3fs | retrieved_chunks=%d",
            retrieval_duration,
            len(retrieved_results),
        )

        try:
            processed_context = self._context_processor.process(retrieved_results)
            prompt = self._prompt_builder.build(normalized_question, processed_context)
        except (PromptBuilderError, PromptValidationError) as exc:
            logger.exception("RAG context or prompt processing failed")
            raise RAGProcessingError("Failed to prepare legal context for generation") from exc
        except Exception as exc:
            logger.exception("Unexpected context or prompt processing failure")
            raise RAGProcessingError(
                "Unexpected failure while preparing legal context"
            ) from exc

        logger.info(
            "RAG context processing completed | processed_chunks=%d",
            processed_context.final_chunk_count,
        )

        try:
            with self._llm_factory() as llm:
                if not isinstance(llm, BaseLLM):
                    raise RAGServiceConfigurationError(
                        "llm_factory must yield a BaseLLM instance"
                    )
                llm_response = llm.generate(prompt.system_prompt, prompt.user_prompt)
        except RAGServiceConfigurationError:
            raise
        except LLMError as exc:
            logger.exception("RAG language-model generation failed")
            raise RAGGenerationError("Failed to generate a legal response") from exc
        except Exception as exc:
            logger.exception("Unexpected language-model generation failure")
            raise RAGGenerationError(
                "Unexpected failure while generating a legal response"
            ) from exc

        pipeline_duration = perf_counter() - pipeline_started_at
        logger.info(
            "RAG generation completed | model=%s | llm_duration=%.3fs",
            llm_response.model_name,
            llm_response.generation_time,
        )
        logger.info("RAG pipeline completed | total_duration=%.3fs", pipeline_duration)

        return RAGResponse(
            question=normalized_question,
            answer=llm_response.answer,
            source_documents=(
                ()
                if self._answer_declares_no_sources(llm_response.answer)
                else prompt.source_documents
            ),
            generation_time=llm_response.generation_time,
            model_name=llm_response.model_name,
            input_token_count=llm_response.input_token_count,
            output_token_count=llm_response.output_token_count,
            finish_reason=llm_response.finish_reason,
            retrieved_chunks_count=len(retrieved_results),
            processed_chunks_count=processed_context.final_chunk_count,
        )

    @staticmethod
    def _validate_question(question: str) -> str:
        if not isinstance(question, str):
            raise RAGValidationError("question must be a string")
        normalized = question.strip()
        if not normalized:
            raise RAGValidationError("question cannot be empty")
        return normalized

    @staticmethod
    def _answer_declares_no_sources(answer: str) -> bool:
        """Return whether the dedicated Sources section explicitly contains None."""
        lines = [line.strip() for line in answer.splitlines()]
        for index in range(len(lines) - 1, -1, -1):
            heading = lines[index].lstrip("#").strip().strip("*_`")
            heading = heading.removesuffix(":").strip()
            if heading.casefold() != "sources":
                continue

            for value in lines[index + 1 :]:
                if not value:
                    continue
                normalized_value = value.lstrip("-*•").strip().strip("*_`).").strip()
                return normalized_value.casefold() == "none"
            return False
        return False
