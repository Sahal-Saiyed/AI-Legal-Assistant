"""Validated request and response schemas for the ask endpoint."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.generated_document import GeneratedDocumentResponse


class SupportedLanguage(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    URDU = "ur"


LANGUAGE_NAMES: dict[SupportedLanguage, str] = {
    SupportedLanguage.ENGLISH: "English",
    SupportedLanguage.HINDI: "Hindi",
    SupportedLanguage.BENGALI: "Bengali",
    SupportedLanguage.TAMIL: "Tamil",
    SupportedLanguage.TELUGU: "Telugu",
    SupportedLanguage.MARATHI: "Marathi",
    SupportedLanguage.GUJARATI: "Gujarati",
    SupportedLanguage.KANNADA: "Kannada",
    SupportedLanguage.MALAYALAM: "Malayalam",
    SupportedLanguage.PUNJABI: "Punjabi",
    SupportedLanguage.URDU: "Urdu",
}


class ConversationContextMessage(BaseModel):
    """A recent turn used only to continue template field collection."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("conversation context content cannot be empty")
        return normalized


class AskRequest(BaseModel):
    """One legal question submitted to the RAG service."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"question": "How do I file an FIR?"},
            ]
        }
    )

    question: str = Field(
        ...,
        min_length=1,
        description="A non-empty legal question for the assistant.",
        examples=["How do I file an FIR?"],
    )
    language: SupportedLanguage = Field(
        default=SupportedLanguage.ENGLISH,
        description="Language used for the generated answer.",
    )
    conversation_context: list[ConversationContextMessage] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Optional recent turns used to collect missing legal-template fields. "
            "They are not treated as retrieval evidence."
        ),
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """Reject whitespace-only questions and normalize surrounding whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("question cannot be empty or whitespace-only")
        return normalized


class AskResponse(BaseModel):
    """Structured legal answer and pipeline metadata."""

    question: str = Field(description="Normalized question submitted by the client.")
    language: SupportedLanguage = Field(description="Language requested for the answer.")
    answer: str = Field(description="Grounded answer generated from retrieved legal context.")
    sources: list[str] = Field(description="Unique source documents available to the answer.")
    generation_time: float = Field(
        ge=0,
        description="Language-model generation duration in seconds.",
    )
    model_name: str = Field(description="Language model used for generation.")
    input_token_count: int | None = Field(
        default=None,
        ge=0,
        description="Input token count when reported by the provider.",
    )
    output_token_count: int | None = Field(
        default=None,
        ge=0,
        description="Output token count when reported by the provider.",
    )
    finish_reason: str | None = Field(
        default=None,
        description="Provider finish reason when available.",
    )
    retrieved_chunks_count: int = Field(
        ge=0,
        description="Number of chunks returned by retrieval.",
    )
    processed_chunks_count: int = Field(
        ge=0,
        description="Number of chunks remaining after context processing.",
    )
    document: GeneratedDocumentResponse | None = Field(
        default=None,
        description="Generated PDF metadata when the question requested a supported legal draft.",
    )
    document_error: str | None = Field(
        default=None,
        description="Non-fatal reason a requested PDF could not be generated.",
    )
