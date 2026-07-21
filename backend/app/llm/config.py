"""Environment-backed configuration for the Gemini LLM provider."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from .base import GenerationParameters
from .exceptions import LLMConfigurationError

DEFAULT_ENV_FILE: Final[Path] = Path(__file__).resolve().parents[3] / ".env"
_REQUIRED_VARIABLES: Final[tuple[str, ...]] = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "TEMPERATURE",
    "MAX_OUTPUT_TOKENS",
    "TIMEOUT",
)


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Validated Gemini configuration loaded from the process environment."""

    api_key: str = field(repr=False)
    model: str
    temperature: float
    max_output_tokens: int
    timeout_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise LLMConfigurationError("GEMINI_API_KEY cannot be empty")
        if not isinstance(self.model, str) or not self.model.strip():
            raise LLMConfigurationError("GEMINI_MODEL cannot be empty")
        self.generation_parameters

    @property
    def generation_parameters(self) -> GenerationParameters:
        """Return validated default generation parameters."""
        return GenerationParameters(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            timeout_seconds=self.timeout_seconds,
        )

    @classmethod
    def from_env(cls, env_file: Path | str | None = None) -> LLMConfig:
        """Load required configuration without overriding process variables."""
        dotenv_path = DEFAULT_ENV_FILE if env_file is None else Path(env_file)
        load_dotenv(dotenv_path=dotenv_path, override=False)

        values = {name: os.getenv(name) for name in _REQUIRED_VARIABLES}
        missing = [name for name, value in values.items() if value is None or not value.strip()]
        if missing:
            raise LLMConfigurationError(
                "Missing required LLM environment variables: " + ", ".join(missing)
            )

        try:
            temperature = float(cls._required_value(values, "TEMPERATURE"))
        except ValueError as exc:
            raise LLMConfigurationError("TEMPERATURE must be a number") from exc
        try:
            max_output_tokens = int(cls._required_value(values, "MAX_OUTPUT_TOKENS"))
        except ValueError as exc:
            raise LLMConfigurationError("MAX_OUTPUT_TOKENS must be an integer") from exc
        try:
            timeout_seconds = float(cls._required_value(values, "TIMEOUT"))
        except ValueError as exc:
            raise LLMConfigurationError("TIMEOUT must be a number of seconds") from exc

        if not math.isfinite(temperature) or not math.isfinite(timeout_seconds):
            raise LLMConfigurationError("TEMPERATURE and TIMEOUT must be finite")

        return cls(
            api_key=cls._required_value(values, "GEMINI_API_KEY").strip(),
            model=cls._required_value(values, "GEMINI_MODEL").strip(),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
        )

    @staticmethod
    def _required_value(values: dict[str, str | None], name: str) -> str:
        value = values[name]
        if value is None:
            raise LLMConfigurationError(f"Missing required LLM environment variable: {name}")
        return value
