"""Semantic document-intent detection using the provider-independent LLM API."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from backend.app.llm import BaseLLM, LLMResponse

from .models import ConversationTurn, TemplateDefinition, TemplateIntent


class TemplateIntentError(RuntimeError):
    """Raised when semantic intent detection returns an invalid decision."""


@dataclass(frozen=True, slots=True)
class DetectedTemplateIntent:
    intent: TemplateIntent
    llm_response: LLMResponse


class LLMTemplateIntentDetector:
    """Classify intent and extract only facts explicitly supplied by the user."""

    def detect(
        self,
        *,
        llm: BaseLLM,
        question: str,
        conversation: tuple[ConversationTurn, ...],
        definitions: tuple[TemplateDefinition, ...],
    ) -> DetectedTemplateIntent:
        catalog = [
            {
                "id": definition.template_id,
                "title": definition.title,
                "aliases": list(definition.aliases),
                "fields": [
                    {"key": field.key, "label": field.label}
                    for field in definition.fields
                ],
            }
            for definition in definitions
        ]
        history = [
            {"role": turn.role, "content": turn.content}
            for turn in conversation[-20:]
        ]
        system_prompt = """
You classify requests for an Indian legal assistant.

Decide whether the user wants:
1. informational: an explanation, legal guidance, procedure, rights, or an example; or
2. document_generation: the assistant to draft, create, prepare, compose, or fill a
   legal document for the user.

Use meaning and conversational context, not exact keyword matching. For example,
"How do I file an FIR?" is informational, while "Prepare my written complaint for
registration of an FIR" is document_generation.

For document_generation, select only a template ID from the supplied catalog.
If the requested format is absent or ambiguous, use null for template_id and put
the requested document name in requested_document.

Extract field values only when the user explicitly supplied them. Never infer names,
addresses, dates, amounts, relationships, property details, or legal facts. Omit
unknown values. Return strict JSON and no prose:
{
  "intent": "informational" | "document_generation",
  "template_id": string | null,
  "requested_document": string | null,
  "fields": {"catalog_field_key": "explicit user value"}
}
""".strip()
        user_prompt = json.dumps(
            {
                "template_catalog": catalog,
                "recent_conversation": history,
                "current_user_message": question,
            },
            ensure_ascii=False,
        )
        response = llm.generate(system_prompt, user_prompt)
        payload = self._parse_json_object(response.answer)
        intent_value = payload.get("intent")
        if intent_value not in {"informational", "document_generation"}:
            raise TemplateIntentError("Intent detector returned an invalid intent")

        valid_ids = {definition.template_id for definition in definitions}
        template_id = payload.get("template_id")
        if template_id is not None and template_id not in valid_ids:
            raise TemplateIntentError("Intent detector selected an unknown template")
        requested_document = payload.get("requested_document")
        if requested_document is not None and not isinstance(requested_document, str):
            raise TemplateIntentError(
                "Intent detector returned an invalid requested document"
            )
        raw_fields = payload.get("fields", {})
        if not isinstance(raw_fields, dict):
            raise TemplateIntentError("Intent detector returned invalid fields")

        allowed_fields = (
            {
                field.key
                for definition in definitions
                if definition.template_id == template_id
                for field in definition.fields
            }
            if template_id
            else set()
        )
        fields: dict[str, str] = {}
        for key, value in raw_fields.items():
            if (
                key in allowed_fields
                and isinstance(value, str)
                and value.strip()
            ):
                fields[key] = value.strip()

        return DetectedTemplateIntent(
            intent=TemplateIntent(
                kind=intent_value,
                template_id=template_id,
                requested_document=(
                    requested_document.strip()
                    if isinstance(requested_document, str)
                    and requested_document.strip()
                    else None
                ),
                fields=fields,
            ),
            llm_response=response,
        )

    @staticmethod
    def _parse_json_object(value: str) -> dict:
        normalized = value.strip()
        normalized = re.sub(r"^```(?:json)?\s*", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*```$", "", normalized)
        start = normalized.find("{")
        end = normalized.rfind("}")
        if start < 0 or end < start:
            raise TemplateIntentError("Intent detector did not return JSON")
        try:
            payload = json.loads(normalized[start : end + 1])
        except json.JSONDecodeError as exc:
            raise TemplateIntentError("Intent detector returned malformed JSON") from exc
        if not isinstance(payload, dict):
            raise TemplateIntentError("Intent detector JSON must be an object")
        return payload

