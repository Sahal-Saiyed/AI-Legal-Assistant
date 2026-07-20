"""Metadata construction for legal knowledge-base documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class MetadataError(ValueError):
    """Raised when required metadata cannot be derived from a file path."""


class DocumentMetadataBuilder:
    """Build consistent metadata from paths inside a knowledge base."""

    def __init__(self, knowledge_base_path: Path, source: str = "official") -> None:
        self._knowledge_base_path = knowledge_base_path.resolve()
        self._source = source

    def build(self, file_path: Path) -> dict[str, Any]:
        """Return metadata derived from a file's knowledge-base-relative path."""
        resolved_path = file_path.resolve()

        try:
            relative_path = resolved_path.relative_to(self._knowledge_base_path)
        except ValueError as exc:
            raise MetadataError(
                f"File is outside the knowledge base: {resolved_path}"
            ) from exc

        if len(relative_path.parts) < 2:
            raise MetadataError(
                "Cannot determine category: documents must be inside a category "
                f"directory under the knowledge base ({relative_path.as_posix()})"
            )

        return {
            "category": relative_path.parts[0],
            "document_name": self._format_document_name(file_path.stem),
            "file_type": file_path.suffix.lower().lstrip("."),
            "source": self._source,
            "relative_path": relative_path.as_posix(),
        }

    @staticmethod
    def _format_document_name(filename_stem: str) -> str:
        normalized = re.sub(r"[_-]+", " ", filename_stem)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            raise MetadataError("Document filename cannot be empty")
        return normalized.title()

