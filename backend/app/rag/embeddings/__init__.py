"""Public interface for embedding legal documents and queries."""

from .base import DocumentEmbedder
from .e5 import DEFAULT_BATCH_SIZE, DEFAULT_MODEL_NAME, E5Embedder

__all__ = ["DEFAULT_BATCH_SIZE", "DEFAULT_MODEL_NAME", "DocumentEmbedder", "E5Embedder"]
