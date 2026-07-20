"""Recursive character-based chunking for legal documents."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from typing import Final

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import DocumentChunker

logger = logging.getLogger(__name__)

DEFAULT_SEPARATORS: Final[tuple[str, ...]] = ("\n\n", "\n", ". ", " ", "")
_CHUNK_ID_VERSION: Final[str] = "legal-assistant-chunk-v1"


class RecursiveDocumentChunker(DocumentChunker):
    """Split documents with LangChain's recursive character splitter."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Sequence[str] = DEFAULT_SEPARATORS,
    ) -> None:
        self._validate_configuration(chunk_size, chunk_overlap, separators)
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separators = tuple(separators)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=list(self._separators),
            length_function=len,
        )

    @property
    def chunk_size(self) -> int:
        """Maximum configured chunk size in characters."""
        return self._chunk_size

    @property
    def chunk_overlap(self) -> int:
        """Configured target overlap in characters."""
        return self._chunk_overlap

    @property
    def separators(self) -> tuple[str, ...]:
        """Separators in descending priority order."""
        return self._separators

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split each document independently, continuing after failures."""
        chunks: list[Document] = []

        for document_index, document in enumerate(documents):
            try:
                chunks.extend(self._split_document(document))
            except Exception:
                logger.exception(
                    "Failed to chunk document at index %d (%s)",
                    document_index,
                    self._document_label(document),
                )

        logger.info(
            "Created %d chunk(s) from %d source document(s)",
            len(chunks),
            len(documents),
        )
        return chunks

    def _split_document(self, document: Document) -> list[Document]:
        document_id = self._create_document_id(document.page_content)
        chunk_texts = [
            text for text in self._splitter.split_text(document.page_content) if text.strip()
        ]
        chunk_count = len(chunk_texts)

        if chunk_count == 0:
            logger.warning("Document produced no non-empty chunks (%s)", self._document_label(document))
            return []

        chunks: list[Document] = []
        for chunk_index, chunk_text in enumerate(chunk_texts):
            metadata = dict(document.metadata)
            metadata.update(
                {
                    "chunk_index": chunk_index,
                    "chunk_count": chunk_count,
                    "chunk_size": len(chunk_text),
                    "chunk_id": self._create_chunk_id(
                        document_id=document_id,
                        chunk_index=chunk_index,
                        chunk_content=chunk_text,
                    ),
                }
            )
            chunks.append(Document(page_content=chunk_text, metadata=metadata))

        return chunks

    @staticmethod
    def _create_document_id(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _create_chunk_id(
        self,
        *,
        document_id: str,
        chunk_index: int,
        chunk_content: str,
    ) -> str:
        identity = {
            "version": _CHUNK_ID_VERSION,
            "document_id": document_id,
            "chunk_index": chunk_index,
            "chunk_content": chunk_content,
            "chunk_size": self._chunk_size,
            "chunk_overlap": self._chunk_overlap,
            "separators": self._separators,
        }
        serialized = json.dumps(
            identity,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _document_label(document: Document) -> str:
        return str(
            document.metadata.get("relative_path")
            or document.metadata.get("document_name")
            or "unknown source"
        )

    @staticmethod
    def _validate_configuration(
        chunk_size: int,
        chunk_overlap: int,
        separators: Sequence[str],
    ) -> None:
        if isinstance(chunk_size, bool) or not isinstance(chunk_size, int):
            raise TypeError("chunk_size must be an integer")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if isinstance(chunk_overlap, bool) or not isinstance(chunk_overlap, int):
            raise TypeError("chunk_overlap must be an integer")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if isinstance(separators, (str, bytes)) or not isinstance(separators, Sequence):
            raise TypeError("separators must be a sequence of strings")
        if not separators:
            raise ValueError("separators cannot be empty")
        if any(not isinstance(separator, str) for separator in separators):
            raise TypeError("every separator must be a string")
