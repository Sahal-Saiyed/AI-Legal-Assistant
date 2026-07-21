"""Public interface for constructing legal prompts."""

from .base import (
    ContextLimitError,
    LegalPrompt,
    PromptBuilder,
    PromptBuilderError,
    PromptValidationError,
)
from .context_processor import (
    DEFAULT_MINIMUM_OVERLAP_TOKENS,
    ContextProcessingResult,
    ContextProcessor,
    ProcessedContextChunk,
)
from .legal_prompt_builder import (
    DEFAULT_MAXIMUM_CONTEXT_CHARACTERS,
    DEFAULT_MAXIMUM_CONTEXT_DOCUMENTS,
    LegalPromptBuilder,
)

__all__ = [
    "ContextLimitError",
    "ContextProcessingResult",
    "ContextProcessor",
    "DEFAULT_MAXIMUM_CONTEXT_CHARACTERS",
    "DEFAULT_MAXIMUM_CONTEXT_DOCUMENTS",
    "DEFAULT_MINIMUM_OVERLAP_TOKENS",
    "LegalPrompt",
    "LegalPromptBuilder",
    "PromptBuilder",
    "PromptBuilderError",
    "PromptValidationError",
    "ProcessedContextChunk",
]
