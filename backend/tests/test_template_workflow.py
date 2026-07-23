"""Unit tests for isolated legal-template routing and PDF generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import fitz
from bson import ObjectId

from backend.app.llm import BaseLLM, LLMResponse
from backend.app.rag.loaders import KnowledgeBaseDocumentLoader
from backend.app.services.document_generation_service import DocumentGenerationService
from backend.app.services.rag_service import RAGService
from backend.app.services.template_service import TemplateService
from backend.app.templates import LegalDocumentDraft, TemplateLoader


class FakeLLM(BaseLLM):
    def __init__(self, answers: list[str]) -> None:
        self._answers = iter(answers)
        self.calls = 0

    def generate(self, system_prompt: str, user_prompt: str, parameters=None) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            answer=next(self._answers),
            model_name="fake-model",
            input_token_count=10,
            output_token_count=5,
            finish_reason="STOP",
            generation_time=0.01,
        )

    def health_check(self) -> bool:
        return True

    def close(self) -> None:
        return None


class RecordingCollection:
    def __init__(self) -> None:
        self.record: dict[str, Any] | None = None

    def insert_one(self, record: dict[str, Any]) -> None:
        self.record = record


class TemplateWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = TemplateLoader()

    def service_for(self, answers: list[str]) -> tuple[TemplateService, FakeLLM]:
        llm = FakeLLM(answers)
        service = TemplateService(
            loader=self.loader,
            llm_factory=lambda: nullcontext(llm),
        )
        return service, llm

    def test_information_request_does_not_load_template(self) -> None:
        service, llm = self.service_for(
            [
                json.dumps(
                    {
                        "intent": "informational",
                        "template_id": None,
                        "requested_document": None,
                        "fields": {},
                    }
                )
            ]
        )
        result = service.process(
            question="What is a lease deed?",
            language="English",
        )
        self.assertIsNone(result)
        self.assertEqual(llm.calls, 1)

    def test_missing_fields_returns_follow_up_without_draft(self) -> None:
        service, llm = self.service_for(
            [
                json.dumps(
                    {
                        "intent": "document_generation",
                        "template_id": "lease_deed",
                        "requested_document": "rent agreement",
                        "fields": {"execution_place": "Delhi"},
                    }
                )
            ]
        )
        result = service.process(
            question="Prepare a rent agreement in Delhi.",
            language="English",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNone(result.draft)
        self.assertIn("date of execution", result.answer)
        self.assertIn("landlord or lessor's full name", result.answer)
        self.assertEqual(llm.calls, 1)

    def test_unsupported_document_request_never_falls_through_to_rag(self) -> None:
        service, _ = self.service_for(
            [
                json.dumps(
                    {
                        "intent": "document_generation",
                        "template_id": None,
                        "requested_document": "consumer complaint",
                        "fields": {},
                    }
                )
            ]
        )
        result = service.process(
            question="Draft a consumer complaint for me.",
            language="English",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNone(result.draft)
        self.assertIn("no matching template", result.answer)

    def test_complete_fields_generate_filled_template(self) -> None:
        definition = self.loader.get_definition("lease_deed")
        values = {
            field.key: f"Supplied {field.label}" for field in definition.required_fields
        }
        service, llm = self.service_for(
            [
                json.dumps(
                    {
                        "intent": "document_generation",
                        "template_id": "lease_deed",
                        "requested_document": "rent agreement",
                        "fields": values,
                    }
                ),
                (
                    "# Lease Deed\n\n"
                    "Date: Supplied date of execution\n\n"
                    "## Parties\n\n"
                    "Supplied landlord or lessor's full name and Supplied tenant or "
                    "lessee's full name agree as follows.\n\n"
                    "## Terms\n\n"
                    "1. The property is leased for the supplied term.\n\n"
                    "## Signatures\n\n"
                    "Lessor: Supplied landlord or lessor's full name\n\n"
                    "Lessee: Supplied tenant or lessee's full name"
                ),
            ]
        )
        result = service.process(
            question="Prepare my rent agreement with all supplied details.",
            language="English",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.draft)
        assert result.draft is not None
        self.assertEqual(result.draft.template_id, "lease_deed")
        self.assertEqual(result.llm_response.input_token_count, 20)
        self.assertEqual(result.llm_response.output_token_count, 10)
        self.assertEqual(llm.calls, 2)

    def test_template_pdf_contains_document_blocks(self) -> None:
        collection = RecordingCollection()
        service = DocumentGenerationService(collection)  # type: ignore[arg-type]
        draft = LegalDocumentDraft(
            template_id="lease_deed",
            document_type="Lease Deed",
            source_template="Lease Deed.pdf",
            content=(
                "# Lease Deed\n\n"
                "Date: 23 July 2026\n\n"
                "Place: Delhi\n\n"
                "## Between\n\n"
                "Asha Verma, the Lessor, and Ravi Kumar, the Lessee.\n\n"
                "## Terms\n\n"
                "1. Monthly rent is Rs. 20,000.\n\n"
                "## Signatures\n\n"
                "Lessor: Asha Verma\n\n"
                "Lessee: Ravi Kumar"
            ),
        )
        response = service.generate_from_template(
            user_id=str(ObjectId()),
            draft=draft,
            language="en",
        )
        self.assertGreater(response.size_bytes, 1000)
        assert collection.record is not None
        pdf_bytes = bytes(collection.record["pdf_data"])
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            text = "\n".join(page.get_text() for page in document)
            self.assertIn("LEASE DEED", text)
            self.assertIn("SIGNATURES", text)
            self.assertIn("Asha Verma", text)

    def test_knowledge_loader_excludes_template_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "consumer").mkdir()
            (root / "templates").mkdir()
            (root / "consumer" / "rights.txt").write_text(
                "Consumer rights content",
                encoding="utf-8",
            )
            (root / "templates" / "notice.txt").write_text(
                "Template content",
                encoding="utf-8",
            )
            documents = KnowledgeBaseDocumentLoader(root).load()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].metadata["category"], "consumer")

    def test_catalog_uses_placeholder_templates(self) -> None:
        for definition in self.loader.definitions():
            loaded = self.loader.load(definition.template_id)
            self.assertTrue(definition.source_file.endswith(".template.md"))
            self.assertIn("{{", loaded.content)

    def test_stale_template_metadata_is_blocked(self) -> None:
        self.assertTrue(
            RAGService._is_template_result(
                {"category": "templates", "relative_path": "templates/old.pdf"}
            )
        )
        self.assertFalse(
            RAGService._is_template_result(
                {"category": "consumer", "relative_path": "consumer/act.pdf"}
            )
        )


if __name__ == "__main__":
    unittest.main()
