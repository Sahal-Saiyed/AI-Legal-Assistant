"""HTTP endpoint for asking one question through the RAG service."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from backend.app.core.dependencies import (
    get_current_user,
    get_document_generation_service,
    get_rag_service,
)
from backend.app.schemas.auth import AuthenticatedUser
from backend.app.schemas.ask import LANGUAGE_NAMES, AskRequest, AskResponse
from backend.app.schemas.generated_document import GeneratedDocumentResponse
from backend.app.services import RAGResponse, RAGService, RAGServiceError
from backend.app.services.document_generation_service import (
    DocumentGenerationError,
    DocumentGenerationService,
)
from backend.app.templates import ConversationTurn

router = APIRouter(tags=["Legal Assistant"])
logger = logging.getLogger(__name__)


def _response_schema(
    request: AskRequest,
    response: RAGResponse,
    document: GeneratedDocumentResponse | None = None,
    document_error: str | None = None,
) -> AskResponse:
    return AskResponse(
        question=response.question,
        language=request.language,
        answer=response.answer,
        sources=list(response.source_documents),
        generation_time=response.generation_time,
        model_name=response.model_name,
        input_token_count=response.input_token_count,
        output_token_count=response.output_token_count,
        finish_reason=response.finish_reason,
        retrieved_chunks_count=response.retrieved_chunks_count,
        processed_chunks_count=response.processed_chunks_count,
        document=document,
        document_error=document_error,
    )


def _generate_document(
    request: AskRequest,
    response: RAGResponse,
    current_user: AuthenticatedUser,
    service: DocumentGenerationService,
) -> tuple[GeneratedDocumentResponse | None, str | None]:
    if response.document_draft is None:
        return None, None
    if request.language.value != "en":
        return (
            None,
            "PDF generation currently supports English drafts only. Select English and ask again.",
        )
    try:
        document = service.generate_from_template(
            user_id=current_user.id,
            draft=response.document_draft,
            language=request.language.value,
        )
        return document, None
    except DocumentGenerationError:
        logger.exception("Legal answer succeeded but PDF generation failed")
        return None, "The legal answer was generated, but its PDF could not be created."


def _conversation_context(request: AskRequest) -> tuple[ConversationTurn, ...]:
    return tuple(
        ConversationTurn(role=message.role, content=message.content)
        for message in request.conversation_context
    )


@router.post(
    "/ask",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a legal question",
    description=(
        "Submit a legal question to the retrieval-augmented assistant and receive "
        "a grounded answer with source and generation metadata."
    ),
)
def ask_question(
    request: AskRequest,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    document_service: Annotated[
        DocumentGenerationService,
        Depends(get_document_generation_service),
    ],
) -> AskResponse:
    """Delegate one validated question to the application service."""
    response = rag_service.ask(
        request.question,
        LANGUAGE_NAMES[request.language],
        _conversation_context(request),
    )
    document, document_error = _generate_document(
        request,
        response,
        current_user,
        document_service,
    )
    return _response_schema(request, response, document, document_error)


@router.post(
    "/ask/stream",
    response_class=StreamingResponse,
    summary="Stream a legal answer",
    description="Stream newline-delimited JSON text deltas followed by final answer metadata.",
)
def stream_question(
    request: AskRequest,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    document_service: Annotated[
        DocumentGenerationService,
        Depends(get_document_generation_service),
    ],
) -> StreamingResponse:
    stream = rag_service.stream(
        request.question,
        LANGUAGE_NAMES[request.language],
        _conversation_context(request),
    )
    first_event = next(stream)

    def serialize(payload: dict) -> bytes:
        return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")

    def event_iterator() -> Iterator[bytes]:
        yield serialize(
            {
                "type": first_event.kind,
                "question": first_event.question,
                "language": request.language.value,
                "retrieved_chunks_count": first_event.retrieved_chunks_count,
                "processed_chunks_count": first_event.processed_chunks_count,
            }
        )
        try:
            for event in stream:
                if event.kind == "delta":
                    yield serialize({"type": "delta", "delta": event.text_delta})
                elif event.kind == "complete" and event.response is not None:
                    document, document_error = _generate_document(
                        request,
                        event.response,
                        current_user,
                        document_service,
                    )
                    response = _response_schema(
                        request,
                        event.response,
                        document,
                        document_error,
                    )
                    yield serialize(
                        {
                            "type": "complete",
                            "response": response.model_dump(mode="json"),
                        }
                    )
        except RAGServiceError as exc:
            logger.exception("RAG stream failed after response started")
            yield serialize({"type": "error", "message": str(exc)})
        except Exception:
            logger.exception("Unexpected RAG stream failure after response started")
            yield serialize(
                {
                    "type": "error",
                    "message": "The legal assistant stream ended unexpectedly.",
                }
            )

    return StreamingResponse(
        event_iterator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
