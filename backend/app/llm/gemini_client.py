"""Gemini implementation of the provider-independent LLM interface."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from .base import BaseLLM, GenerationParameters, LLMResponse
from .config import LLMConfig
from .exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMGenerationError,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLM):
    """Generate text through Google's current Gen AI SDK."""

    def __init__(
        self,
        config: LLMConfig,
        client: genai.Client | None = None,
    ) -> None:
        if not isinstance(config, LLMConfig):
            raise TypeError("config must be an LLMConfig")
        self._config = config
        self._owns_client = client is None
        self._closed = False
        try:
            self._client = client or genai.Client(api_key=config.api_key)
        except Exception as exc:
            logger.exception("Failed to initialize Gemini client for model %s", config.model)
            raise LLMConfigurationError("Failed to initialize the Gemini client") from exc
        logger.info("Initialized Gemini client for model %s", config.model)

    @property
    def model_name(self) -> str:
        """Configured Gemini model identifier."""
        return self._config.model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        parameters: GenerationParameters | None = None,
    ) -> LLMResponse:
        """Generate a normalized, non-streaming Gemini response."""
        self._ensure_open()
        normalized_system, normalized_user = self.validate_prompts(
            system_prompt,
            user_prompt,
        )
        effective_parameters = parameters or self._config.generation_parameters
        if not isinstance(effective_parameters, GenerationParameters):
            raise TypeError("parameters must be GenerationParameters or None")

        prompt_size = len(normalized_system) + len(normalized_user)
        logger.info(
            "Starting Gemini generation | model=%s | prompt_size=%d",
            self.model_name,
            prompt_size,
        )
        started_at = perf_counter()

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=normalized_user,
                config=types.GenerateContentConfig(
                    system_instruction=normalized_system,
                    temperature=float(effective_parameters.temperature),
                    max_output_tokens=effective_parameters.max_output_tokens,
                    http_options=types.HttpOptions(
                        timeout=self._timeout_milliseconds(
                            effective_parameters.timeout_seconds
                        )
                    ),
                ),
            )
            generation_time = perf_counter() - started_at
            llm_response = self._parse_response(response, generation_time)
        except (LLMGenerationError, LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError):
            raise
        except errors.APIError as exc:
            self._raise_api_error(exc)
        except (httpx.TimeoutException, TimeoutError) as exc:
            logger.error("Gemini generation timed out | model=%s", self.model_name)
            raise LLMTimeoutError("Gemini generation timed out") from exc
        except Exception as exc:
            logger.exception("Gemini generation failed | model=%s", self.model_name)
            raise LLMGenerationError("Gemini generation failed") from exc

        logger.info(
            "Completed Gemini generation | model=%s | duration=%.3fs | "
            "response_size=%d | input_tokens=%s | output_tokens=%s",
            llm_response.model_name,
            llm_response.generation_time,
            len(llm_response.answer),
            llm_response.input_token_count,
            llm_response.output_token_count,
        )
        return llm_response

    def health_check(self) -> bool:
        """Check authentication, connectivity, and configured-model availability."""
        self._ensure_open()
        logger.info("Checking Gemini model health | model=%s", self.model_name)
        try:
            self._client.models.get(
                model=self.model_name,
                config=types.GetModelConfig(
                    http_options=types.HttpOptions(
                        timeout=self._timeout_milliseconds(self._config.timeout_seconds)
                    )
                ),
            )
        except errors.APIError as exc:
            self._raise_api_error(exc)
        except (httpx.TimeoutException, TimeoutError) as exc:
            logger.error("Gemini health check timed out | model=%s", self.model_name)
            raise LLMTimeoutError("Gemini health check timed out") from exc
        except Exception as exc:
            logger.exception("Gemini health check failed | model=%s", self.model_name)
            raise LLMGenerationError("Gemini health check failed") from exc

        logger.info("Gemini health check passed | model=%s", self.model_name)
        return True

    def close(self) -> None:
        """Close an internally owned SDK client exactly once."""
        if self._closed:
            return
        if self._owns_client:
            self._client.close()
        self._closed = True
        logger.debug("Closed Gemini client | model=%s", self.model_name)

    def __enter__(self) -> GeminiClient:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()

    def _parse_response(
        self,
        response: types.GenerateContentResponse,
        generation_time: float,
    ) -> LLMResponse:
        answer = response.text
        finish_reason = self._finish_reason(response)
        if not isinstance(answer, str) or not answer.strip():
            detail = f" (finish reason: {finish_reason})" if finish_reason else ""
            raise LLMGenerationError(f"Gemini returned an empty response{detail}")

        usage = response.usage_metadata
        return LLMResponse(
            answer=answer.strip(),
            model_name=self.model_name,
            input_token_count=self._optional_non_negative_integer(
                getattr(usage, "prompt_token_count", None) if usage else None
            ),
            output_token_count=self._optional_non_negative_integer(
                getattr(usage, "candidates_token_count", None) if usage else None
            ),
            finish_reason=finish_reason,
            generation_time=generation_time,
        )

    @staticmethod
    def _finish_reason(response: types.GenerateContentResponse) -> str | None:
        if not response.candidates:
            return None
        reason = response.candidates[0].finish_reason
        if reason is None:
            return None
        value = getattr(reason, "value", reason)
        return str(value)

    @staticmethod
    def _optional_non_negative_integer(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise LLMGenerationError("Gemini returned invalid token usage metadata")
        return value

    @staticmethod
    def _timeout_milliseconds(timeout_seconds: float) -> int:
        return max(1, round(timeout_seconds * 1000))

    def _ensure_open(self) -> None:
        if self._closed:
            raise LLMGenerationError("Gemini client is closed")

    def _raise_api_error(self, error: errors.APIError) -> None:
        status_code = int(error.code)
        logger.error(
            "Gemini API error | model=%s | status=%d | error_type=%s",
            self.model_name,
            status_code,
            type(error).__name__,
        )
        if status_code in {401, 403}:
            raise LLMAuthenticationError("Gemini authentication or authorization failed") from error
        if status_code == 429:
            raise LLMRateLimitError("Gemini rate limit exceeded") from error
        if status_code in {408, 504}:
            raise LLMTimeoutError("Gemini request timed out") from error
        raise LLMGenerationError(
            f"Gemini request failed with HTTP status {status_code}"
        ) from error
