"""Load legal output templates exclusively from ``knowledge_base/templates``."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Final

import fitz

from .models import LoadedTemplate, TemplateDefinition, TemplateField

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_ROOT: Final[Path] = (
    Path(__file__).resolve().parents[3] / "knowledge_base" / "templates"
)
CATALOG_FILENAME: Final[str] = "catalog.json"
SUPPORTED_TEMPLATE_SUFFIXES: Final[frozenset[str]] = frozenset({".pdf", ".md", ".txt"})


class TemplateLoaderError(RuntimeError):
    """Raised when the isolated template catalog cannot be loaded safely."""


class TemplateNotFoundError(TemplateLoaderError):
    """Raised when a requested template is absent from the catalog."""


class TemplateLoader:
    """Validate a template catalog and lazily load its source files."""

    def __init__(self, template_root: Path | str = DEFAULT_TEMPLATE_ROOT) -> None:
        self._template_root = Path(template_root).resolve()
        self._definitions = self._load_catalog()
        self._content_cache: dict[str, LoadedTemplate] = {}
        logger.info(
            "Loaded legal template catalog | path=%s | templates=%d",
            self._template_root,
            len(self._definitions),
        )

    @property
    def template_root(self) -> Path:
        return self._template_root

    def definitions(self) -> tuple[TemplateDefinition, ...]:
        return tuple(self._definitions.values())

    def get_definition(self, template_id: str) -> TemplateDefinition:
        try:
            return self._definitions[template_id]
        except KeyError as exc:
            raise TemplateNotFoundError(f"Unknown legal template: {template_id}") from exc

    def load(self, template_id: str) -> LoadedTemplate:
        cached = self._content_cache.get(template_id)
        if cached is not None:
            return cached

        definition = self.get_definition(template_id)
        source_path = self._safe_source_path(definition.source_file)
        suffix = source_path.suffix.casefold()
        try:
            if suffix == ".pdf":
                content = self._extract_pdf_text(source_path)
            else:
                content = source_path.read_text(encoding="utf-8")
        except (OSError, RuntimeError, ValueError) as exc:
            raise TemplateLoaderError(
                f"Unable to read template source: {definition.source_file}"
            ) from exc

        normalized = content.strip()
        if not normalized:
            raise TemplateLoaderError(
                f"Template source is empty: {definition.source_file}"
            )
        loaded = LoadedTemplate(definition=definition, content=normalized)
        self._content_cache[template_id] = loaded
        logger.info(
            "Loaded template source | template_id=%s | source=%s | characters=%d",
            template_id,
            definition.source_file,
            len(normalized),
        )
        return loaded

    def _load_catalog(self) -> dict[str, TemplateDefinition]:
        if not self._template_root.is_dir():
            raise TemplateLoaderError(
                f"Template directory does not exist: {self._template_root}"
            )
        catalog_path = self._template_root / CATALOG_FILENAME
        try:
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TemplateLoaderError(
                f"Unable to load template catalog: {catalog_path}"
            ) from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("templates"), list):
            raise TemplateLoaderError("Template catalog must contain a templates array")

        definitions: dict[str, TemplateDefinition] = {}
        for index, raw_definition in enumerate(payload["templates"]):
            definition = self._parse_definition(raw_definition, index)
            if definition.template_id in definitions:
                raise TemplateLoaderError(
                    f"Duplicate template ID in catalog: {definition.template_id}"
                )
            self._safe_source_path(definition.source_file)
            definitions[definition.template_id] = definition
        if not definitions:
            raise TemplateLoaderError("Template catalog cannot be empty")
        return definitions

    def _safe_source_path(self, source_file: str) -> Path:
        source_path = (self._template_root / source_file).resolve()
        try:
            source_path.relative_to(self._template_root)
        except ValueError as exc:
            raise TemplateLoaderError(
                f"Template source escapes the template directory: {source_file}"
            ) from exc
        if source_path.suffix.casefold() not in SUPPORTED_TEMPLATE_SUFFIXES:
            raise TemplateLoaderError(
                f"Unsupported template source type: {source_path.suffix}"
            )
        if not source_path.is_file():
            raise TemplateLoaderError(f"Template source does not exist: {source_file}")
        return source_path

    @staticmethod
    def _parse_definition(raw: Any, index: int) -> TemplateDefinition:
        if not isinstance(raw, dict):
            raise TemplateLoaderError(f"Template catalog entry {index} must be an object")

        def required_string(key: str) -> str:
            value = raw.get(key)
            if not isinstance(value, str) or not value.strip():
                raise TemplateLoaderError(
                    f"Template catalog entry {index} has invalid {key!r}"
                )
            return value.strip()

        aliases = raw.get("aliases")
        fields = raw.get("fields")
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) and alias.strip() for alias in aliases
        ):
            raise TemplateLoaderError(
                f"Template catalog entry {index} has invalid aliases"
            )
        if not isinstance(fields, list) or not fields:
            raise TemplateLoaderError(
                f"Template catalog entry {index} must define fields"
            )

        parsed_fields: list[TemplateField] = []
        field_keys: set[str] = set()
        for field_index, raw_field in enumerate(fields):
            if not isinstance(raw_field, dict):
                raise TemplateLoaderError(
                    f"Template field {index}:{field_index} must be an object"
                )
            key = raw_field.get("key")
            label = raw_field.get("label")
            required = raw_field.get("required", True)
            if (
                not isinstance(key, str)
                or not key.strip()
                or not isinstance(label, str)
                or not label.strip()
                or not isinstance(required, bool)
            ):
                raise TemplateLoaderError(
                    f"Template field {index}:{field_index} is invalid"
                )
            normalized_key = key.strip()
            if normalized_key in field_keys:
                raise TemplateLoaderError(
                    f"Duplicate field {normalized_key!r} in catalog entry {index}"
                )
            field_keys.add(normalized_key)
            parsed_fields.append(
                TemplateField(
                    key=normalized_key,
                    label=label.strip(),
                    required=required,
                )
            )

        return TemplateDefinition(
            template_id=required_string("id"),
            title=required_string("title"),
            source_file=required_string("source_file"),
            aliases=tuple(alias.strip() for alias in aliases),
            fields=tuple(parsed_fields),
        )

    @staticmethod
    def _extract_pdf_text(source_path: Path) -> str:
        with fitz.open(source_path) as document:
            return "\n\n".join(page.get_text("text") for page in document)

