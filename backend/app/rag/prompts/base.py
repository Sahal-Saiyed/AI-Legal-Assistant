"""Interfaces, result types, and exceptions for prompt construction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context_processor import ContextProcessingResult


class PromptBuilderError(RuntimeError):
    """Base exception for prompt-construction failures."""


class PromptValidationError(ValueError):
    """Raised when prompt input or configuration is invalid."""


class ContextLimitError(PromptBuilderError):
    """Raised when no complete retrieved chunk fits the context limit."""


@dataclass(frozen=True, slots=True)
class LegalPrompt:
    """Complete structured prompt produced for a legal question."""

    system_prompt: str
    user_prompt: str
    formatted_context: str
    question: str
    source_documents: tuple[str, ...]


class PromptBuilder(ABC):
    """Construct a prompt from a question and retrieved evidence."""

    @abstractmethod
    def build(
        self,
        question: str,
        processed_context: ContextProcessingResult,
        language: str = "English",
    ) -> LegalPrompt:
        """Return one structured prompt without invoking a language model."""
