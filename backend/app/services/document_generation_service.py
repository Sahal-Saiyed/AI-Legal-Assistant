"""Generate and securely persist grounded legal-document PDFs."""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from bson import Binary, ObjectId
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from backend.app.schemas.generated_document import GeneratedDocumentResponse
from backend.app.templates import LegalDocumentDraft

logger = logging.getLogger(__name__)

DOCUMENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (
        label,
        re.compile(
            rf"\b(?:draft|prepare|create|generate|write|make|compose)\b"
            rf".{{0,60}}\b(?:{terms})\b|"
            rf"\b(?:{terms})\b.{{0,60}}\b(?:draft|prepare|create|generate|write|make|compose)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    )
    for label, terms in (
        ("Complaint", r"complaint|grievance"),
        ("Legal Notice", r"legal\s+notice|demand\s+notice|notice"),
        ("Application", r"application|formal\s+request"),
        ("Representation", r"representation"),
        ("Reply", r"reply|response\s+letter"),
    )
)


class DocumentGenerationError(RuntimeError):
    """Raised when a requested document cannot be generated or loaded."""


class GeneratedDocumentNotFoundError(DocumentGenerationError):
    """Raised when a generated file is unavailable to the current user."""


class DocumentGenerationService:
    """Detect drafting intent and store compact PDF artifacts in MongoDB."""

    def __init__(self, documents: Collection) -> None:
        self._documents = documents

    def generate_if_requested(
        self,
        *,
        user_id: str,
        question: str,
        answer: str,
        sources: tuple[str, ...],
        language: str,
    ) -> GeneratedDocumentResponse | None:
        document_type = self.detect_document_type(question)
        if document_type is None:
            return None
        if language != "en":
            logger.info(
                "Skipping PDF artifact because configured PDF fonts do not support language=%s",
                language,
            )
            return None

        owner_id = self._owner_id(user_id)
        document_id = str(uuid4())
        filename = f"{self._slug(document_type)}-{document_id[:8]}.pdf"
        created_at = datetime.now(timezone.utc)
        pdf_data = self._build_pdf(
            document_type=document_type,
            answer=answer,
            sources=sources,
            created_at=created_at,
        )
        record = {
            "_id": document_id,
            "user_id": owner_id,
            "filename": filename,
            "document_type": document_type,
            "media_type": "application/pdf",
            "size_bytes": len(pdf_data),
            "created_at": created_at,
            "pdf_data": Binary(pdf_data),
        }
        try:
            self._documents.insert_one(record)
        except PyMongoError as exc:
            logger.exception("Failed to persist generated document | user_id=%s", user_id)
            raise DocumentGenerationError("Unable to save the generated PDF") from exc
        logger.info(
            "Generated legal PDF | user_id=%s | document_id=%s | type=%s | bytes=%d",
            user_id,
            document_id,
            document_type,
            len(pdf_data),
        )
        return self._response(record)

    def generate_from_template(
        self,
        *,
        user_id: str,
        draft: LegalDocumentDraft,
        language: str,
    ) -> GeneratedDocumentResponse:
        """Render and persist a filled template instead of a chat-response PDF."""
        if not isinstance(draft, LegalDocumentDraft):
            raise TypeError("draft must be a LegalDocumentDraft")
        if language != "en":
            raise DocumentGenerationError(
                "PDF generation currently supports English legal templates only"
            )

        owner_id = self._owner_id(user_id)
        document_id = str(uuid4())
        filename = f"{self._slug(draft.document_type)}-{document_id[:8]}.pdf"
        created_at = datetime.now(timezone.utc)
        pdf_data = self._build_template_pdf(draft=draft, created_at=created_at)
        record = {
            "_id": document_id,
            "user_id": owner_id,
            "filename": filename,
            "document_type": draft.document_type,
            "template_id": draft.template_id,
            "source_template": draft.source_template,
            "media_type": "application/pdf",
            "size_bytes": len(pdf_data),
            "created_at": created_at,
            "pdf_data": Binary(pdf_data),
        }
        try:
            self._documents.insert_one(record)
        except PyMongoError as exc:
            logger.exception(
                "Failed to persist template document | user_id=%s | template_id=%s",
                user_id,
                draft.template_id,
            )
            raise DocumentGenerationError("Unable to save the generated PDF") from exc
        logger.info(
            "Generated template PDF | user_id=%s | document_id=%s | "
            "template_id=%s | bytes=%d",
            user_id,
            document_id,
            draft.template_id,
            len(pdf_data),
        )
        return self._response(record)

    def load(self, user_id: str, document_id: str) -> tuple[GeneratedDocumentResponse, bytes]:
        owner_id = self._owner_id(user_id)
        try:
            record = self._documents.find_one(
                {"_id": document_id, "user_id": owner_id}
            )
        except PyMongoError as exc:
            logger.exception("Failed to load generated document | user_id=%s", user_id)
            raise DocumentGenerationError("Unable to load the generated PDF") from exc
        if not record:
            raise GeneratedDocumentNotFoundError("Generated document was not found")
        return self._response(record), bytes(record["pdf_data"])

    @staticmethod
    def detect_document_type(question: str) -> str | None:
        normalized = " ".join(question.split())
        for document_type, pattern in DOCUMENT_PATTERNS:
            if pattern.search(normalized):
                return document_type
        return None

    @classmethod
    def _build_pdf(
        cls,
        *,
        document_type: str,
        answer: str,
        sources: tuple[str, ...],
        created_at: datetime,
    ) -> bytes:
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=22 * mm,
            leftMargin=22 * mm,
            topMargin=28 * mm,
            bottomMargin=22 * mm,
            title=f"{document_type} Draft",
            author="JuriGPT",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocumentTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#123c36"),
            spaceAfter=5 * mm,
        )
        heading_style = ParagraphStyle(
            "DocumentHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#176b5b"),
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        )
        body_style = ParagraphStyle(
            "DocumentBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#263b38"),
            spaceAfter=2.5 * mm,
        )
        note_style = ParagraphStyle(
            "DocumentNote",
            parent=body_style,
            fontSize=8.5,
            leading=13,
            textColor=colors.HexColor("#61736f"),
            backColor=colors.HexColor("#eef7f4"),
            borderPadding=8,
            spaceAfter=5 * mm,
        )

        story: list = [
            Paragraph(f"{html.escape(document_type)} Draft", title_style),
            Paragraph(
                "Generated from the facts supplied by the user and the legal material "
                "available to JuriGPT. Review all names, dates, addresses, claims, and "
                "requested relief before use.",
                note_style,
            ),
        ]
        story.extend(cls._answer_flowables(answer, body_style, heading_style))
        if sources:
            story.extend(
                [
                    Spacer(1, 4 * mm),
                    Paragraph("Reference Documents", heading_style),
                    ListFlowable(
                        [
                            ListItem(Paragraph(html.escape(source), body_style))
                            for source in sources
                        ],
                        bulletType="bullet",
                        leftIndent=16,
                    ),
                ]
            )
        story.extend(
            [
                Spacer(1, 6 * mm),
                Paragraph(
                    "<b>Important:</b> This is an automatically generated draft for "
                    "informational purposes and is not legal advice. A qualified advocate "
                    "should review it before filing, serving, signing, or relying on it.",
                    note_style,
                ),
            ]
        )

        def draw_page(canvas, doc) -> None:
            canvas.saveState()
            width, height = A4
            canvas.setFillColor(colors.HexColor("#123c36"))
            canvas.rect(0, height - 12 * mm, width, 12 * mm, stroke=0, fill=1)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 10)
            canvas.drawString(22 * mm, height - 7.5 * mm, "JuriGPT")
            canvas.setFillColor(colors.HexColor("#6d7d79"))
            canvas.setFont("Helvetica", 8)
            footer = f"Generated {created_at:%d %b %Y}  |  Page {doc.page}"
            canvas.drawRightString(width - 22 * mm, 10 * mm, footer)
            canvas.restoreState()

        document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
        return buffer.getvalue()

    @classmethod
    def _build_template_pdf(
        cls,
        *,
        draft: LegalDocumentDraft,
        created_at: datetime,
    ) -> bytes:
        """Render a filled legal template with document-style spacing and blocks."""
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=25 * mm,
            leftMargin=25 * mm,
            topMargin=25 * mm,
            bottomMargin=22 * mm,
            title=draft.document_type,
            author="JuriGPT",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "LegalTemplateTitle",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=16,
            leading=21,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=7 * mm,
            keepWithNext=True,
        )
        heading_style = ParagraphStyle(
            "LegalTemplateHeading",
            parent=styles["Heading2"],
            fontName="Times-Bold",
            fontSize=11.5,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
        )
        body_style = ParagraphStyle(
            "LegalTemplateBody",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=17,
            alignment=TA_LEFT,
            firstLineIndent=7 * mm,
            textColor=colors.black,
            spaceAfter=3 * mm,
            allowWidows=0,
            allowOrphans=0,
        )
        block_style = ParagraphStyle(
            "LegalTemplateBlock",
            parent=body_style,
            firstLineIndent=0,
            leading=16,
            spaceAfter=2 * mm,
        )
        story: list = [Paragraph(html.escape(draft.document_type.upper()), title_style)]
        story.extend(
            cls._template_flowables(
                draft.content,
                body_style=body_style,
                block_style=block_style,
                heading_style=heading_style,
                document_title=draft.document_type,
            )
        )

        def draw_page(canvas, doc) -> None:
            canvas.saveState()
            width, _ = A4
            canvas.setStrokeColor(colors.HexColor("#b8c7c3"))
            canvas.setLineWidth(0.5)
            canvas.line(25 * mm, 16 * mm, width - 25 * mm, 16 * mm)
            canvas.setFillColor(colors.HexColor("#5c6865"))
            canvas.setFont("Helvetica", 8)
            canvas.drawString(25 * mm, 10 * mm, f"JuriGPT | {draft.document_type}")
            canvas.drawRightString(
                width - 25 * mm,
                10 * mm,
                f"{created_at:%d %b %Y} | Page {doc.page}",
            )
            canvas.restoreState()

        document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
        return buffer.getvalue()

    @classmethod
    def _template_flowables(
        cls,
        content: str,
        *,
        body_style: ParagraphStyle,
        block_style: ParagraphStyle,
        heading_style: ParagraphStyle,
        document_title: str,
    ) -> list:
        flowables: list = []
        title_skipped = False
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if re.fullmatch(r"[-_*]{3,}", line):
                flowables.append(Spacer(1, 3 * mm))
                continue
            heading = re.match(r"^#{1,6}\s+(.+)$", line)
            if heading:
                heading_text = heading.group(1).strip()
                if (
                    not title_skipped
                    and heading_text.casefold() == document_title.casefold()
                ):
                    title_skipped = True
                    continue
                flowables.append(
                    Paragraph(cls._inline_markup(heading_text.upper()), heading_style)
                )
                continue
            bullet = re.match(r"^(?:[-*]|\u2022)\s+(.+)$", line)
            if bullet:
                flowables.append(
                    ListFlowable(
                        [
                            ListItem(
                                Paragraph(
                                    cls._inline_markup(bullet.group(1)),
                                    block_style,
                                )
                            )
                        ],
                        bulletType="bullet",
                        leftIndent=8 * mm,
                    )
                )
                continue
            if re.match(r"^\d+[.)]\s+(.+)$", line):
                flowables.append(Paragraph(cls._inline_markup(line), block_style))
                continue
            is_block = bool(
                re.match(
                    r"^(?:date|place|to|from|address|witness|signature|"
                    r"lessor|lessee|vendor|vendee|donor|donee|principal|"
                    r"attorney|testator|executor)\b",
                    line,
                    re.IGNORECASE,
                )
            )
            flowables.append(
                Paragraph(
                    cls._inline_markup(line),
                    block_style if is_block else body_style,
                )
            )
        return flowables

    @classmethod
    def _answer_flowables(
        cls,
        answer: str,
        body_style: ParagraphStyle,
        heading_style: ParagraphStyle,
    ) -> list:
        content = cls._without_metadata_sections(answer)
        flowables: list = []
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                flowables.append(Spacer(1, 1.5 * mm))
                continue
            heading = re.match(r"^#{1,6}\s+(.+)$", line)
            if heading:
                flowables.append(Paragraph(cls._inline_markup(heading.group(1)), heading_style))
                continue
            bullet = re.match(r"^(?:[-*]|\u2022)\s+(.+)$", line)
            if bullet:
                flowables.append(
                    ListFlowable(
                        [ListItem(Paragraph(cls._inline_markup(bullet.group(1)), body_style))],
                        bulletType="bullet",
                        leftIndent=16,
                    )
                )
                continue
            numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
            if numbered:
                flowables.append(Paragraph(cls._inline_markup(line), body_style))
                continue
            flowables.append(Paragraph(cls._inline_markup(line), body_style))
        return flowables

    @staticmethod
    def _without_metadata_sections(answer: str) -> str:
        lines = answer.splitlines()
        for index, line in enumerate(lines):
            heading = line.strip().lstrip("#").strip().strip("*_").rstrip(":").casefold()
            if heading in {"sources", "disclaimer"}:
                return "\n".join(lines[:index]).strip()
        return answer.strip()

    @staticmethod
    def _inline_markup(value: str) -> str:
        escaped = html.escape(value)
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")

    @staticmethod
    def _owner_id(user_id: str) -> ObjectId:
        if not ObjectId.is_valid(user_id):
            raise DocumentGenerationError("Invalid authenticated user identifier")
        return ObjectId(user_id)

    @staticmethod
    def _response(record: dict) -> GeneratedDocumentResponse:
        document_id = str(record["_id"])
        return GeneratedDocumentResponse(
            id=document_id,
            filename=record["filename"],
            document_type=record["document_type"],
            media_type=record["media_type"],
            size_bytes=record["size_bytes"],
            created_at=record["created_at"],
            download_url=f"/api/v1/documents/{document_id}",
        )
