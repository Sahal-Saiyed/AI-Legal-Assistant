"""Orchestrate legal document intent, field collection, and template filling."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import replace
from typing import TypeAlias

from backend.app.llm import BaseLLM, LLMError, LLMResponse
from backend.app.templates import (
    ConversationTurn,
    LLMPlaceholderFiller,
    LLMTemplateIntentDetector,
    LegalDocumentDraft,
    PlaceholderFillingError,
    TemplateIntentError,
    TemplateLoader,
    TemplateLoaderError,
    TemplateServiceResult,
)

logger = logging.getLogger(__name__)

ManagedLLMFactory: TypeAlias = Callable[[], AbstractContextManager[BaseLLM]]


class TemplateServiceError(RuntimeError):
    """Raised when the isolated document-template workflow fails."""


class TemplateService:
    """Route document requests without retrieving template content through RAG."""

    def __init__(
        self,
        *,
        loader: TemplateLoader,
        llm_factory: ManagedLLMFactory,
        intent_detector: LLMTemplateIntentDetector | None = None,
        placeholder_filler: LLMPlaceholderFiller | None = None,
    ) -> None:
        if not isinstance(loader, TemplateLoader):
            raise TypeError("loader must be a TemplateLoader")
        if not callable(llm_factory):
            raise TypeError("llm_factory must be callable")
        self._loader = loader
        self._llm_factory = llm_factory
        self._intent_detector = intent_detector or LLMTemplateIntentDetector()
        self._placeholder_filler = placeholder_filler or LLMPlaceholderFiller()

    def process(
        self,
        *,
        question: str,
        language: str,
        conversation: tuple[ConversationTurn, ...] = (),
    ) -> TemplateServiceResult | None:
        """Return ``None`` for knowledge questions or a document-workflow response."""
        try:
            with self._llm_factory() as llm:
                if not isinstance(llm, BaseLLM):
                    raise TemplateServiceError(
                        "llm_factory must yield a BaseLLM instance"
                    )
                detected = self._intent_detector.detect(
                    llm=llm,
                    question=question,
                    conversation=conversation,
                    definitions=self._loader.definitions(),
                )
                intent = detected.intent
                if intent.kind == "informational":
                    logger.info("Template intent classified as informational")
                    return None

                if intent.template_id is None:
                    return TemplateServiceResult(
                        answer=self._unsupported_template_answer(
                            intent.requested_document
                        ),
                        llm_response=detected.llm_response,
                    )

                definition = self._loader.get_definition(intent.template_id)
                missing_fields = [
                    field
                    for field in definition.required_fields
                    if not intent.fields.get(field.key, "").strip()
                ]
                if missing_fields:
                    logger.info(
                        "Template requires follow-up | template_id=%s | missing_fields=%d",
                        definition.template_id,
                        len(missing_fields),
                    )
                    return TemplateServiceResult(
                        answer=self._missing_fields_answer(
                            definition.title,
                            tuple(field.label for field in missing_fields),
                        ),
                        llm_response=detected.llm_response,
                    )

                if language.casefold() != "english":
                    return TemplateServiceResult(
                        answer=(
                            "JuriGPT currently generates legal document templates and "
                            "their PDF files in English only. Please select English and "
                            "submit the document request again."
                        ),
                        llm_response=detected.llm_response,
                    )

                template = self._loader.load(intent.template_id)
                filled_response = self._placeholder_filler.fill(
                    llm=llm,
                    template=template,
                    values=intent.fields,
                )
                draft = LegalDocumentDraft(
                    template_id=definition.template_id,
                    document_type=definition.title,
                    source_template=definition.source_file,
                    content=filled_response.answer,
                )
                combined_response = self._combine_usage(
                    detected.llm_response,
                    filled_response,
                )
                answer = (
                    f"{draft.content}\n\n"
                    "## Disclaimer\n"
                    "This document was prepared from the selected template and only "
                    "the information supplied in this conversation. It is a draft for "
                    "informational purposes, not legal advice. Have a qualified advocate "
                    "review it before filing, serving, signing, or relying on it."
                )
                logger.info(
                    "Generated filled legal template | template_id=%s | characters=%d",
                    definition.template_id,
                    len(draft.content),
                )
                return TemplateServiceResult(
                    answer=answer,
                    llm_response=replace(combined_response, answer=answer),
                    draft=draft,
                )
        except TemplateServiceError:
            raise
        except (TemplateLoaderError, TemplateIntentError, PlaceholderFillingError) as exc:
            logger.exception("Legal template processing failed")
            raise TemplateServiceError("Failed to prepare the legal document") from exc
        except LLMError as exc:
            logger.exception("Legal template language-model request failed")
            raise TemplateServiceError(
                "Failed to process the legal document request"
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected legal template processing failure")
            raise TemplateServiceError(
                "Unexpected failure while processing the legal document request"
            ) from exc

    def _unsupported_template_answer(self, requested_document: str | None) -> str:
        requested = requested_document or "that legal document"
        available = "\n".join(
            f"- {definition.title}" for definition in self._loader.definitions()
        )
        return (
            f"I understood that you want JuriGPT to prepare {requested}, but no matching "
            "template is currently available in the isolated template catalog.\n\n"
            "Available document templates:\n"
            f"{available}\n\n"
            "No document was generated, and no knowledge-base chunks were used."
        )

    @staticmethod
    def _missing_fields_answer(
        document_type: str,
        missing_labels: tuple[str, ...],
    ) -> str:
        fields = "\n".join(f"- {label}" for label in missing_labels)
        return (
            f"To prepare the **{document_type}** without inventing any facts, please "
            "provide the following information:\n\n"
            f"{fields}\n\n"
            "Reply with these details in this conversation. JuriGPT will keep using "
            "the selected template and will not guess missing values."
        )

    @staticmethod
    def _combine_usage(
        intent_response: LLMResponse,
        fill_response: LLMResponse,
    ) -> LLMResponse:
        def add_optional(left: int | None, right: int | None) -> int | None:
            if left is None and right is None:
                return None
            return (left or 0) + (right or 0)

        return LLMResponse(
            answer=fill_response.answer,
            model_name=fill_response.model_name,
            input_token_count=add_optional(
                intent_response.input_token_count,
                fill_response.input_token_count,
            ),
            output_token_count=add_optional(
                intent_response.output_token_count,
                fill_response.output_token_count,
            ),
            finish_reason=fill_response.finish_reason,
            generation_time=(
                intent_response.generation_time + fill_response.generation_time
            ),
        )

