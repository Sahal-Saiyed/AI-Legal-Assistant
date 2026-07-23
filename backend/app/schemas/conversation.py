"""Validated schemas for persisted user conversations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.generated_document import GeneratedDocumentResponse


class ConversationSource(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)


class UserConversationMessage(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    role: Literal["user"]
    content: str = Field(min_length=1, max_length=20_000)
    timestamp: datetime


class AssistantConversationMessage(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    role: Literal["assistant"]
    answer: list[str] = Field(min_length=1, max_length=100)
    sources: list[ConversationSource] = Field(default_factory=list, max_length=100)
    disclaimer: str = Field(max_length=5_000)
    timestamp: datetime
    generation_time: float = Field(ge=0)
    language: str = Field(default="en", min_length=2, max_length=10)
    document: GeneratedDocumentResponse | None = None
    document_error: str | None = Field(default=None, max_length=500)


ConversationMessage = Annotated[
    UserConversationMessage | AssistantConversationMessage,
    Field(discriminator="role"),
]


class ConversationWriteRequest(BaseModel):
    title: str = Field(min_length=1, max_length=72)
    title_customized: bool = False
    messages: list[ConversationMessage] = Field(min_length=1, max_length=500)
    updated_at: datetime

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("conversation title cannot be empty")
        return normalized


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=72)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("conversation title cannot be empty")
        return normalized


class ConversationResponse(ConversationWriteRequest):
    id: str
    created_at: datetime
