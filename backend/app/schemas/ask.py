"""Validated request and response schemas for the ask endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
