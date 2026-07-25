"""Application service that orchestrates the legal retrieval-augmented pipeline."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from time import perf_counter
from typing import Literal, TypeAlias

from backend.app.llm import BaseLLM, LLMError, LLMResponse
from backend.app.rag.prompts import (
    ContextProcessor,
    LegalPromptBuilder,
    LegalPrompt,
    PromptBuilder,
    PromptBuilderError,
    PromptValidationError,
)
from backend.app.rag.retrieval import RetrievalError, Retriever
from backend.app.templates import ConversationTurn, LegalDocumentDraft, TemplateServiceResult

from .template_service import TemplateService, TemplateServiceError

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
    language: str
    answer: str
    source_documents: tuple[str, ...]
    generation_time: float
    model_name: str
    input_token_count: int | None
    output_token_count: int | None
    finish_reason: str | None
    retrieved_chunks_count: int
    processed_chunks_count: int
    document_draft: LegalDocumentDraft | None = None


@dataclass(frozen=True, slots=True)
class PreparedRAGRequest:
    question: str
    language: str
    prompt: LegalPrompt
    retrieved_chunks_count: int
    processed_chunks_count: int


@dataclass(frozen=True, slots=True)
class RAGStreamEvent:
    kind: Literal["metadata", "delta", "complete"]
    text_delta: str = ""
    response: RAGResponse | None = None
    question: str | None = None
    language: str | None = None
    retrieved_chunks_count: int | None = None
    processed_chunks_count: int | None = None


class RAGService:
    """Coordinate independent retrieval, context, prompt, and LLM components."""

    def __init__(
        self,
        retriever: Retriever,
        context_processor: ContextProcessor,
        prompt_builder: PromptBuilder,
        llm_factory: ManagedLLMFactory,
        template_service: TemplateService | None = None,
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
        if template_service is not None and not isinstance(
            template_service, TemplateService
        ):
            raise RAGServiceConfigurationError(
                "template_service must be a TemplateService or None"
            )

        self._retriever = retriever
        self._context_processor = context_processor
        self._prompt_builder = prompt_builder
        self._llm_factory = llm_factory
        self._template_service = template_service

    @classmethod
    def from_env(cls) -> RAGService:
        """Build the current production pipeline from environment configuration."""
        from backend.app.llm import GeminiClient, LLMConfig
        from backend.app.rag.embeddings import E5Embedder
        from backend.app.rag.retrieval import ChromaRetriever
        from backend.app.templates import TemplateLoader

        llm_config = LLMConfig.from_env()
        embedding_model = os.getenv("E5_MODEL_NAME", "intfloat/e5-base-v2").strip()
        if not embedding_model:
            raise RAGServiceConfigurationError("E5_MODEL_NAME cannot be empty")
        retriever = ChromaRetriever(embedder=E5Embedder(model_name=embedding_model))
        llm_factory = lambda: GeminiClient(llm_config)
        return cls(
            retriever=retriever,
            context_processor=ContextProcessor(),
            prompt_builder=LegalPromptBuilder(),
            llm_factory=llm_factory,
            template_service=TemplateService(
                loader=TemplateLoader(),
                llm_factory=llm_factory,
            ),
        )

    def ask(
        self,
        question: str,
        language: str = "English",
        conversation: tuple[ConversationTurn, ...] = (),
    ) -> RAGResponse:
        """Run one validated question through the complete RAG pipeline."""
        pipeline_started_at = perf_counter()
        normalized_question = self._validate_question(question)
        normalized_language = self._validate_language(language)
        template_result = self._process_template_request(
            normalized_question,
            normalized_language,
            conversation,
        )
        if template_result is not None:
            logger.info(
                "Template pipeline completed | total_duration=%.3fs | draft=%s",
                perf_counter() - pipeline_started_at,
                template_result.draft is not None,
            )
            return self._build_template_response(
                normalized_question,
                normalized_language,
                template_result,
            )

        prepared = self._prepare(normalized_question, normalized_language)

        try:
            with self._llm_factory() as llm:
                if not isinstance(llm, BaseLLM):
                    raise RAGServiceConfigurationError(
                        "llm_factory must yield a BaseLLM instance"
                    )
                llm_response = llm.generate(
                    prepared.prompt.system_prompt,
                    prepared.prompt.user_prompt,
                )
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

        return self._build_response(prepared, llm_response)

    def stream(
        self,
        question: str,
        language: str = "English",
        conversation: tuple[ConversationTurn, ...] = (),
    ) -> Iterator[RAGStreamEvent]:
        """Stream one grounded answer while retaining final structured metadata."""
        normalized_question = self._validate_question(question)
        normalized_language = self._validate_language(language)
        template_result = self._process_template_request(
            normalized_question,
            normalized_language,
            conversation,
        )
        if template_result is not None:
            response = self._build_template_response(
                normalized_question,
                normalized_language,
                template_result,
            )
            yield RAGStreamEvent(
                kind="metadata",
                question=normalized_question,
                language=normalized_language,
                retrieved_chunks_count=0,
                processed_chunks_count=0,
            )
            yield RAGStreamEvent(kind="delta", text_delta=response.answer)
            yield RAGStreamEvent(kind="complete", response=response)
            return

        prepared = self._prepare(normalized_question, normalized_language)
        yield RAGStreamEvent(
            kind="metadata",
            question=prepared.question,
            language=prepared.language,
            retrieved_chunks_count=prepared.retrieved_chunks_count,
            processed_chunks_count=prepared.processed_chunks_count,
        )

        final_response: LLMResponse | None = None
        try:
            with self._llm_factory() as llm:
                if not isinstance(llm, BaseLLM):
                    raise RAGServiceConfigurationError(
                        "llm_factory must yield a BaseLLM instance"
                    )
                for event in llm.stream_generate(
                    prepared.prompt.system_prompt,
                    prepared.prompt.user_prompt,
                ):
                    if event.text_delta:
                        yield RAGStreamEvent(kind="delta", text_delta=event.text_delta)
                    if event.response is not None:
                        final_response = event.response
        except RAGServiceConfigurationError:
            raise
        except LLMError as exc:
            logger.exception("RAG streamed language-model generation failed")
            raise RAGGenerationError("Failed to generate a legal response") from exc
        except Exception as exc:
            logger.exception("Unexpected streamed language-model generation failure")
            raise RAGGenerationError(
                "Unexpected failure while generating a legal response"
            ) from exc

        if final_response is None:
            raise RAGGenerationError("Language model stream ended without metadata")
        yield RAGStreamEvent(
            kind="complete",
            response=self._build_response(prepared, final_response),
        )

    def _prepare(self, question: str, language: str) -> PreparedRAGRequest:
        normalized_question = self._validate_question(question)
        normalized_language = self._validate_language(language)
        logger.info(
            "Received RAG question | question_length=%d | language=%s",
            len(normalized_question),
            normalized_language,
        )
        retrieval_started_at = perf_counter()
        try:
            retrieved_results = self._retriever.retrieve(normalized_question)
        except RetrievalError as exc:
            logger.exception("RAG retrieval failed")
            raise RAGRetrievalError("Failed to retrieve legal context") from exc
        except Exception as exc:
            logger.exception("Unexpected retrieval failure")
            raise RAGRetrievalError("Unexpected failure while retrieving legal context") from exc

        knowledge_results = [
            result
            for result in retrieved_results
            if not self._is_template_result(result.metadata)
        ]
        removed_template_chunks = len(retrieved_results) - len(knowledge_results)
        if removed_template_chunks:
            logger.error(
                "Blocked %d stale template chunk(s) from the RAG context; rebuild "
                "the vector collection",
                removed_template_chunks,
            )
        retrieved_results = knowledge_results
        if not retrieved_results:
            raise RAGRetrievalError(
                "No legal knowledge chunks were available after template isolation. "
                "Rebuild the Chroma collection from the current knowledge base."
            )

        logger.info(
            "RAG retrieval completed | duration=%.3fs | retrieved_chunks=%d",
            perf_counter() - retrieval_started_at,
            len(retrieved_results),
        )
        try:
            processed_context = self._context_processor.process(retrieved_results)
            prompt = self._prompt_builder.build(
                normalized_question,
                processed_context,
                normalized_language,
            )
        except (PromptBuilderError, PromptValidationError) as exc:
            logger.exception("RAG context or prompt processing failed")
            raise RAGProcessingError("Failed to prepare legal context for generation") from exc
        except Exception as exc:
            logger.exception("Unexpected context or prompt processing failure")
            raise RAGProcessingError(
                "Unexpected failure while preparing legal context"
            ) from exc
        return PreparedRAGRequest(
            question=normalized_question,
            language=normalized_language,
            prompt=prompt,
            retrieved_chunks_count=len(retrieved_results),
            processed_chunks_count=processed_context.final_chunk_count,
        )

    def _build_response(
        self,
        prepared: PreparedRAGRequest,
        llm_response: LLMResponse,
    ) -> RAGResponse:
        return RAGResponse(
            question=prepared.question,
            language=prepared.language,
            answer=llm_response.answer,
            source_documents=(
                ()
                if self._answer_declares_no_sources(llm_response.answer)
                else prepared.prompt.source_documents
            ),
            generation_time=llm_response.generation_time,
            model_name=llm_response.model_name,
            input_token_count=llm_response.input_token_count,
            output_token_count=llm_response.output_token_count,
            finish_reason=llm_response.finish_reason,
            retrieved_chunks_count=prepared.retrieved_chunks_count,
            processed_chunks_count=prepared.processed_chunks_count,
        )

    def _process_template_request(
        self,
        question: str,
        language: str,
        conversation: tuple[ConversationTurn, ...],
    ) -> TemplateServiceResult | None:
        if self._template_service is None:
            return None
        if not isinstance(conversation, tuple) or any(
            not isinstance(turn, ConversationTurn) for turn in conversation
        ):
            raise RAGValidationError(
                "conversation must be a tuple of ConversationTurn objects"
            )
        try:
            return self._template_service.process(
                question=question,
                language=language,
                conversation=conversation,
            )
        except TemplateServiceError as exc:
            raise RAGGenerationError(
                "Failed to process the legal document request"
            ) from exc

    @staticmethod
    def _build_template_response(
        question: str,
        language: str,
        result: TemplateServiceResult,
    ) -> RAGResponse:
        llm_response = result.llm_response
        return RAGResponse(
            question=question,
            language=language,
            answer=result.answer,
            source_documents=(),
            generation_time=llm_response.generation_time,
            model_name=llm_response.model_name,
            input_token_count=llm_response.input_token_count,
            output_token_count=llm_response.output_token_count,
            finish_reason=llm_response.finish_reason,
            retrieved_chunks_count=0,
            processed_chunks_count=0,
            document_draft=result.draft,
        )

    @staticmethod
    def _is_template_result(metadata: dict) -> bool:
        category = str(metadata.get("category", "")).strip().casefold()
        relative_path = str(metadata.get("relative_path", "")).replace("\\", "/")
        return category == "templates" or relative_path.casefold().startswith(
            "templates/"
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
    def _validate_language(language: str) -> str:
        if not isinstance(language, str):
            raise RAGValidationError("language must be a string")
        normalized = " ".join(language.split())
        if not normalized or len(normalized) > 50:
            raise RAGValidationError("language must be a valid language name")
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
