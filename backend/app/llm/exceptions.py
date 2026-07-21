"""Provider-independent exceptions raised by the LLM layer."""

from __future__ import annotations


class LLMError(RuntimeError):
    """Base exception for language-model operations."""


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration is missing or invalid."""


class LLMAuthenticationError(LLMError):
    """Raised when an LLM provider rejects authentication or authorization."""


class LLMRateLimitError(LLMError):
    """Raised when an LLM provider rate limit is exceeded."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request exceeds its configured timeout."""


class LLMGenerationError(LLMError):
    """Raised when an LLM cannot produce a valid response."""
