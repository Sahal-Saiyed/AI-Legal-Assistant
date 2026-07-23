"""Legal output-template components, isolated from the RAG knowledge pipeline."""

from .intent_detector import (
    DetectedTemplateIntent,
    LLMTemplateIntentDetector,
    TemplateIntentError,
)
from .models import (
    ConversationTurn,
    LegalDocumentDraft,
    LoadedTemplate,
    TemplateDefinition,
    TemplateField,
    TemplateIntent,
    TemplateServiceResult,
)
from .placeholder_filler import LLMPlaceholderFiller, PlaceholderFillingError
from .template_loader import (
    DEFAULT_TEMPLATE_ROOT,
    TemplateLoader,
    TemplateLoaderError,
    TemplateNotFoundError,
)

__all__ = [
    "ConversationTurn",
    "DEFAULT_TEMPLATE_ROOT",
    "DetectedTemplateIntent",
    "LLMPlaceholderFiller",
    "LLMTemplateIntentDetector",
    "LegalDocumentDraft",
    "LoadedTemplate",
    "PlaceholderFillingError",
    "TemplateDefinition",
    "TemplateField",
    "TemplateIntent",
    "TemplateIntentError",
    "TemplateLoader",
    "TemplateLoaderError",
    "TemplateNotFoundError",
    "TemplateServiceResult",
]
