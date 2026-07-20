"""Format-specific loaders that produce one document per source file."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pymupdf
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document

from .base import SourceFileLoader


class PlainTextFileLoader(SourceFileLoader):
    """Load a UTF-8 text-based file into a single document."""

    def load(self, file_path: Path, metadata: Mapping[str, Any]) -> Document:
        loaded_documents = TextLoader(
            str(file_path),
            encoding="utf-8-sig",
            autodetect_encoding=False,
        ).load()
        if len(loaded_documents) != 1:
            raise ValueError(
                f"Expected one document from {file_path}, got {len(loaded_documents)}"
            )

        return Document(
            page_content=loaded_documents[0].page_content,
            metadata=dict(metadata),
        )


class PdfFileLoader(SourceFileLoader):
    """Load all pages of a PDF into one page-boundary-preserving document."""

    PAGE_SEPARATOR = "========== PAGE {page_number} =========="

    def load(self, file_path: Path, metadata: Mapping[str, Any]) -> Document:
        page_sections: list[str] = []

        with pymupdf.open(file_path) as pdf_document:
            if pdf_document.needs_pass:
                raise ValueError(f"Password-protected PDF cannot be read: {file_path}")

            page_count = pdf_document.page_count
            for page_number, page in enumerate(pdf_document, start=1):
                extracted_text = page.get_text("text").strip()
                separator = self.PAGE_SEPARATOR.format(page_number=page_number)
                page_sections.append(f"{separator}\n{extracted_text}")

        document_metadata = dict(metadata)
        document_metadata["page_count"] = page_count

        return Document(
            page_content="\n\n".join(page_sections),
            metadata=document_metadata,
        )
