"""Authenticated conversation persistence endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.app.core.dependencies import get_conversation_service, get_current_user
from backend.app.schemas.auth import AuthenticatedUser
from backend.app.schemas.conversation import (
    ConversationRenameRequest,
    ConversationResponse,
    ConversationWriteRequest,
)
from backend.app.services.conversation_service import (
    ConversationConflictError,
    ConversationNotFoundError,
    ConversationService,
    ConversationServiceError,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def _service_error(exception: ConversationServiceError) -> HTTPException:
    if isinstance(exception, ConversationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exception))
    if isinstance(exception, ConversationConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exception))
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exception),
    )


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> list[ConversationResponse]:
    try:
        return service.list_for_user(user.id)
    except ConversationServiceError as exc:
        raise _service_error(exc) from exc


@router.put("/{conversation_id}", response_model=ConversationResponse)
def save_conversation(
    conversation_id: str,
    request: ConversationWriteRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    try:
        return service.save(user.id, conversation_id, request)
    except ConversationServiceError as exc:
        raise _service_error(exc) from exc


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def rename_conversation(
    conversation_id: str,
    request: ConversationRenameRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    try:
        return service.rename(user.id, conversation_id, request)
    except ConversationServiceError as exc:
        raise _service_error(exc) from exc


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Response:
    try:
        service.delete(user.id, conversation_id)
    except ConversationServiceError as exc:
        raise _service_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
