"""Interfaces and shared types for source-file loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping

from langchain_core.documents import Document


class SourceFileLoader(ABC):
    """Load one source file into exactly one LangChain document."""

    @abstractmethod
    def load(self, file_path: Path, metadata: Mapping[str, Any]) -> Document:
        """Load ``file_path`` and attach the supplied metadata."""

