"""Recursive document loader for the legal knowledge base."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping

from langchain_core.documents import Document

from .base import SourceFileLoader
from .file_loaders import PdfFileLoader, PlainTextFileLoader
from .metadata import DocumentMetadataBuilder

logger = logging.getLogger(__name__)


class KnowledgeBaseDocumentLoader:
    """Discover and load supported knowledge-base files."""

    def __init__(self, knowledge_base_path: Path | str) -> None:
        self._knowledge_base_path = Path(knowledge_base_path).resolve()
        text_loader = PlainTextFileLoader()
        self._loaders: Mapping[str, SourceFileLoader] = {
            ".pdf": PdfFileLoader(),
            ".md": text_loader,
            ".txt": text_loader,
        }
        self._metadata_builder = DocumentMetadataBuilder(self._knowledge_base_path)

    def load(self) -> list[Document]:
        """Load every supported file, continuing when an individual file fails."""
        self._validate_knowledge_base()
        documents: list[Document] = []

        for file_path in self._discover_supported_files():
            try:
                metadata = self._metadata_builder.build(file_path)
                file_loader = self._loaders[file_path.suffix.lower()]
                documents.append(file_loader.load(file_path, metadata))
                logger.info("Loaded document: %s", metadata["relative_path"])
            except Exception:
                logger.exception("Failed to load document: %s", file_path)

        logger.info("Loaded %d document(s) from %s", len(documents), self._knowledge_base_path)
        return documents

    def _validate_knowledge_base(self) -> None:
        if not self._knowledge_base_path.exists():
            raise FileNotFoundError(
                f"Knowledge base directory does not exist: {self._knowledge_base_path}"
            )
        if not self._knowledge_base_path.is_dir():
            raise NotADirectoryError(
                f"Knowledge base path is not a directory: {self._knowledge_base_path}"
            )

    def _discover_supported_files(self) -> list[Path]:
        files = (
            path
            for path in self._knowledge_base_path.rglob("*")
            if path.is_file() and path.suffix.lower() in self._loaders
        )
        return sorted(
            files,
            key=lambda path: path.relative_to(self._knowledge_base_path).as_posix().lower(),
        )

