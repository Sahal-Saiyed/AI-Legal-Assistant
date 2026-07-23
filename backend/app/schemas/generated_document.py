"""Schemas for generated legal-document artifacts."""

from datetime import datetime

from pydantic import BaseModel, Field


class GeneratedDocumentResponse(BaseModel):
    id: str
    filename: str
    document_type: str
    media_type: str = "application/pdf"
    size_bytes: int = Field(ge=1)
    created_at: datetime
    download_url: str
