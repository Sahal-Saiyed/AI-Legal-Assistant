"""Provider-neutral models used by the legal template workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from backend.app.llm import LLMResponse


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """One recent conversation turn supplied for follow-up field collection."""

    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class TemplateField:
    """One user-provided value required by a legal template."""

    key: str
    label: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class TemplateDefinition:
    """Catalog metadata for one template stored outside the knowledge index."""

    template_id: str
    title: str
    source_file: str
    aliases: tuple[str, ...]
    fields: tuple[TemplateField, ...]

    @property
    def required_fields(self) -> tuple[TemplateField, ...]:
        return tuple(field for field in self.fields if field.required)


@dataclass(frozen=True, slots=True)
class LoadedTemplate:
    """A validated catalog definition and its source-format content."""

    definition: TemplateDefinition
    content: str


@dataclass(frozen=True, slots=True)
class TemplateIntent:
    """Structured result of semantic intent and fact extraction."""

    kind: Literal["informational", "document_generation"]
    template_id: str | None
    requested_document: str | None
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LegalDocumentDraft:
    """Filled legal document ready for formatted text and PDF rendering."""

    template_id: str
    document_type: str
    source_template: str
    content: str


@dataclass(frozen=True, slots=True)
class TemplateServiceResult:
    """A document workflow response, with a draft only when all fields exist."""

    answer: str
    llm_response: LLMResponse
    draft: LegalDocumentDraft | None = None

