"""Populate legal template placeholders without inventing user facts."""

from __future__ import annotations

import json
import re

from backend.app.llm import BaseLLM, LLMResponse

from .models import LoadedTemplate


class PlaceholderFillingError(RuntimeError):
    """Raised when a legal template cannot be populated safely."""


class LLMPlaceholderFiller:
    """Use an LLM to adapt a source format using only validated field values."""

    def fill(
        self,
        *,
        llm: BaseLLM,
        template: LoadedTemplate,
        values: dict[str, str],
    ) -> LLMResponse:
        known_placeholders = set(
            re.findall(r"\{\{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*\}\}", template.content)
        )
        unknown_placeholders = known_placeholders.difference(values)
        if unknown_placeholders:
            missing = ", ".join(sorted(unknown_placeholders))
            raise PlaceholderFillingError(
                f"Template has unresolved mandatory placeholders: {missing}"
            )

        system_prompt = """
You fill a legal document format for India.

Rules:
- Preserve the source template's legal structure, headings, clause order, date and
  address blocks, numbered provisions, witness area, and signature blocks.
- Use only the supplied user values for case-specific facts.
- Never invent a name, address, date, amount, property description, relationship,
  registration detail, event, legal claim, or signature.
- Replace template blanks and placeholders with the matching supplied values.
- Remove source-publication headers, page numbers, explanatory model notes, and
  blank calculation fields that do not apply to the final document.
- Do not add legal sections or factual recitals absent from the source template.
- Return only the completed legal document in clean Markdown.
- Use one H1 title, H2 section headings, normal paragraphs, numbered clauses, and
  clearly separated date, place, witness, and signature blocks.
- Do not include chat commentary, sources, a disclaimer, or Markdown code fences.
""".strip()
        user_prompt = (
            "TEMPLATE DEFINITION:\n"
            f"{template.definition.title}\n\n"
            "USER-SUPPLIED VALUES:\n"
            f"{json.dumps(values, ensure_ascii=False, indent=2)}\n\n"
            "SOURCE TEMPLATE:\n"
            f"{template.content}"
        )
        response = llm.generate(system_prompt, user_prompt)
        content = self._clean_document(response.answer)
        return LLMResponse(
            answer=content,
            model_name=response.model_name,
            input_token_count=response.input_token_count,
            output_token_count=response.output_token_count,
            finish_reason=response.finish_reason,
            generation_time=response.generation_time,
        )

    @staticmethod
    def _clean_document(value: str) -> str:
        normalized = value.strip()
        normalized = re.sub(r"^```(?:markdown|md)?\s*", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*```$", "", normalized)
        if not normalized:
            raise PlaceholderFillingError("Template filler returned an empty document")
        unresolved = re.findall(
            r"\{\{\s*[a-zA-Z][a-zA-Z0-9_]*\s*\}\}",
            normalized,
        )
        if unresolved:
            raise PlaceholderFillingError(
                "Template filler returned unresolved placeholders"
            )
        return normalized

