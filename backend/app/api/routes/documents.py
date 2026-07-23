"""Authenticated downloads for generated legal-document PDFs."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.app.core.dependencies import (
    get_current_user,
    get_document_generation_service,
)
from backend.app.schemas.auth import AuthenticatedUser
from backend.app.services.document_generation_service import (
    DocumentGenerationError,
    DocumentGenerationService,
    GeneratedDocumentNotFoundError,
)

router = APIRouter(prefix="/documents", tags=["Generated Documents"])


@router.get(
    "/{document_id}",
    response_class=Response,
    summary="Download a generated legal PDF",
)
def download_document(
    document_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[
        DocumentGenerationService,
        Depends(get_document_generation_service),
    ],
) -> Response:
    try:
        metadata, content = service.load(user.id, document_id)
    except GeneratedDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return Response(
        content=content,
        media_type=metadata.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{metadata.filename}"',
            "Content-Length": str(len(content)),
            "Cache-Control": "private, no-store",
        },
    )
