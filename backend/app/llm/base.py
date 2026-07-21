"""Provider-independent language-model contracts and value objects."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .exceptions import LLMConfigurationError


@dataclass(frozen=True, slots=True)
class GenerationParameters:
    """Validated parameters shared by text-generation providers."""

    temperature: float
    max_output_tokens: int
    timeout_seconds: float

    def __post_init__(self) -> None:
        if isinstance(self.temperature, bool) or not isinstance(
            self.temperature, (int, float)
        ):
            raise LLMConfigurationError("temperature must be a number")
        if not math.isfinite(float(self.temperature)) or not 0 <= self.temperature <= 2:
            raise LLMConfigurationError("temperature must be between 0 and 2")
        if isinstance(self.max_output_tokens, bool) or not isinstance(
            self.max_output_tokens, int
        ):
            raise LLMConfigurationError("max_output_tokens must be an integer")
        if self.max_output_tokens <= 0:
            raise LLMConfigurationError("max_output_tokens must be greater than zero")
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise LLMConfigurationError("timeout_seconds must be a number")
        if not math.isfinite(float(self.timeout_seconds)) or self.timeout_seconds <= 0:
            raise LLMConfigurationError("timeout_seconds must be greater than zero")


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Normalized response returned by every language-model provider."""

    answer: str
    model_name: str
    input_token_count: int | None
    output_token_count: int | None
    finish_reason: str | None
    generation_time: float


class BaseLLM(ABC):
    """Provider-neutral synchronous language-model interface."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        parameters: GenerationParameters | None = None,
    ) -> LLMResponse:
        """Generate one response from independent system and user prompts."""

    @abstractmethod
    def health_check(self) -> bool:
        """Validate provider connectivity, authentication, and model availability."""

    @abstractmethod
    def close(self) -> None:
        """Release provider client resources."""

    @staticmethod
    def validate_prompts(system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """Validate and normalize provider-independent prompt input."""
        if not isinstance(system_prompt, str):
            raise TypeError("system_prompt must be a string")
        if not isinstance(user_prompt, str):
            raise TypeError("user_prompt must be a string")
        normalized_system_prompt = system_prompt.strip()
        normalized_user_prompt = user_prompt.strip()
        if not normalized_system_prompt:
            raise LLMConfigurationError("system_prompt cannot be empty")
        if not normalized_user_prompt:
            raise LLMConfigurationError("user_prompt cannot be empty")
        return normalized_system_prompt, normalized_user_prompt
