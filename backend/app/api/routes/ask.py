"""HTTP endpoint for asking one question through the RAG service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.app.core.dependencies import get_rag_service
from backend.app.schemas.ask import AskRequest, AskResponse
from backend.app.services import RAGService

router = APIRouter(tags=["Legal Assistant"])


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
) -> AskResponse:
    """Delegate one validated question to the application service."""
    response = rag_service.ask(request.question)
    return AskResponse(
        question=response.question,
        answer=response.answer,
        sources=list(response.source_documents),
        generation_time=response.generation_time,
        model_name=response.model_name,
        input_token_count=response.input_token_count,
        output_token_count=response.output_token_count,
        finish_reason=response.finish_reason,
        retrieved_chunks_count=response.retrieved_chunks_count,
        processed_chunks_count=response.processed_chunks_count,
    )
