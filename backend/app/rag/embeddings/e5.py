"""Hugging Face implementation of the E5 embedding model."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Final, cast

import torch
import torch.nn.functional as functional
from langchain_core.documents import Document
from transformers import AutoModel, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from .base import DocumentEmbedder

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME: Final[str] = "intfloat/e5-base-v2"
DEFAULT_BATCH_SIZE: Final[int] = 32
DOCUMENT_PREFIX: Final[str] = "passage: "
QUERY_PREFIX: Final[str] = "query: "


class E5Embedder(DocumentEmbedder):
    """Generate normalized E5 embeddings for chunks and search queries."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = DEFAULT_BATCH_SIZE,
        device: str | None = None,
    ) -> None:
        self._validate_configuration(model_name, batch_size)
        self._model_name = model_name
        self._batch_size = batch_size
        self._device = self._resolve_device(device)

        logger.info("Loading embedding model %s on %s", model_name, self._device)
        self._tokenizer: PreTrainedTokenizerBase = AutoTokenizer.from_pretrained(model_name)
        self._model: PreTrainedModel = AutoModel.from_pretrained(model_name)
        self._model.to(self._device)
        self._model.eval()
        self._max_length = self._resolve_max_length()
        logger.info(
            "Loaded embedding model %s (maximum sequence length: %d)",
            model_name,
            self._max_length,
        )

    @property
    def model_name(self) -> str:
        """Hugging Face model identifier used by this embedder."""
        return self._model_name

    @property
    def batch_size(self) -> int:
        """Maximum number of texts processed in one inference batch."""
        return self._batch_size

    @property
    def device(self) -> str:
        """Device used for model inference."""
        return str(self._device)

    def embed_documents(self, documents: list[Document]) -> list[list[float]]:
        """Embed chunk documents with E5's passage prefix, preserving order."""
        texts: list[str] = []
        for index, document in enumerate(documents):
            if not isinstance(document.page_content, str) or not document.page_content.strip():
                raise ValueError(f"Document at index {index} has empty page content")
            texts.append(f"{DOCUMENT_PREFIX}{document.page_content}")

        if not texts:
            return []

        logger.info(
            "Embedding %d document(s) in batches of up to %d",
            len(texts),
            self._batch_size,
        )
        embeddings = self._embed_texts(texts)
        logger.info("Embedded %d document(s)", len(embeddings))
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed one query with E5's query prefix."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not query.strip():
            raise ValueError("query cannot be empty")

        logger.debug("Embedding query")
        return self._embed_texts([f"{QUERY_PREFIX}{query}"])[0]

    def _embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), self._batch_size):
            batch = texts[batch_start : batch_start + self._batch_size]
            try:
                embeddings.extend(self._embed_batch(batch))
            except Exception:
                logger.exception(
                    "Failed to embed batch starting at index %d with %d text(s)",
                    batch_start,
                    len(batch),
                )
                raise

        return embeddings

    def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        encoded = self._tokenizer(
            list(texts),
            max_length=self._max_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        encoded = {name: tensor.to(self._device) for name, tensor in encoded.items()}

        with torch.inference_mode():
            model_output = self._model(**encoded)
            pooled = self._average_pool(
                model_output.last_hidden_state,
                encoded["attention_mask"],
            )
            normalized = functional.normalize(pooled, p=2, dim=1)

        return cast(list[list[float]], normalized.cpu().tolist())

    @staticmethod
    def _average_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Mean-pool token embeddings while excluding padding tokens."""
        mask = attention_mask.unsqueeze(-1).to(last_hidden_state.dtype)
        summed_embeddings = torch.sum(last_hidden_state * mask, dim=1)
        token_counts = torch.sum(mask, dim=1).clamp(min=1e-9)
        return summed_embeddings / token_counts

    def _resolve_max_length(self) -> int:
        tokenizer_limit = self._tokenizer.model_max_length
        model_limit = getattr(self._model.config, "max_position_embeddings", tokenizer_limit)
        valid_limits = [
            limit
            for limit in (tokenizer_limit, model_limit)
            if isinstance(limit, int) and 0 < limit < 1_000_000
        ]
        if not valid_limits:
            raise ValueError(f"Could not determine maximum sequence length for {self._model_name}")
        return min(valid_limits)

    @staticmethod
    def _resolve_device(device: str | None) -> torch.device:
        if device is None:
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")

        resolved = torch.device(device)
        if resolved.type == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA was requested but is not available")
        return resolved

    @staticmethod
    def _validate_configuration(model_name: str, batch_size: int) -> None:
        if not isinstance(model_name, str):
            raise TypeError("model_name must be a string")
        if not model_name.strip():
            raise ValueError("model_name cannot be empty")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int):
            raise TypeError("batch_size must be an integer")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
