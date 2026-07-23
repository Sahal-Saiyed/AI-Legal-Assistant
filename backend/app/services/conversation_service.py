"""MongoDB persistence operations for authenticated conversations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from backend.app.schemas.conversation import (
    ConversationRenameRequest,
    ConversationResponse,
    ConversationWriteRequest,
)

logger = logging.getLogger(__name__)


class ConversationServiceError(RuntimeError):
    """Base failure raised by conversation persistence."""


class ConversationNotFoundError(ConversationServiceError):
    """Raised when a conversation is unavailable to the current user."""


class ConversationConflictError(ConversationServiceError):
    """Raised when a conversation identifier is already in use."""


class ConversationService:
    """Persist conversations while enforcing per-user ownership."""

    def __init__(self, conversations: Collection) -> None:
        self._conversations = conversations

    def list_for_user(self, user_id: str) -> list[ConversationResponse]:
        owner_id = self._owner_id(user_id)
        try:
            documents = self._conversations.find(
                {"user_id": owner_id},
            ).sort("updated_at", -1).limit(200)
            return [self._to_response(document) for document in documents]
        except PyMongoError as exc:
            logger.exception("Failed to list conversations | user_id=%s", user_id)
            raise ConversationServiceError("Unable to load conversations") from exc

    def save(
        self,
        user_id: str,
        conversation_id: str,
        request: ConversationWriteRequest,
    ) -> ConversationResponse:
        self._validate_conversation_id(conversation_id)
        owner_id = self._owner_id(user_id)
        now = datetime.now(timezone.utc)
        try:
            existing = self._conversations.find_one(
                {"_id": conversation_id},
                {"user_id": 1, "created_at": 1},
            )
        except PyMongoError as exc:
            logger.exception(
                "Failed to inspect conversation | user_id=%s | conversation_id=%s",
                user_id,
                conversation_id,
            )
            raise ConversationServiceError("Unable to save conversation") from exc
        if existing and existing.get("user_id") != owner_id:
            raise ConversationNotFoundError("Conversation was not found")

        payload = request.model_dump(mode="python")
        payload.update(
            {
                "_id": conversation_id,
                "user_id": owner_id,
                "created_at": existing.get("created_at", now) if existing else now,
                "updated_at": now,
            }
        )
        try:
            self._conversations.replace_one(
                {"_id": conversation_id, "user_id": owner_id},
                payload,
                upsert=True,
            )
        except DuplicateKeyError as exc:
            raise ConversationConflictError("Conversation identifier is already in use") from exc
        except PyMongoError as exc:
            logger.exception(
                "Failed to save conversation | user_id=%s | conversation_id=%s",
                user_id,
                conversation_id,
            )
            raise ConversationServiceError("Unable to save conversation") from exc

        logger.info(
            "Saved conversation | user_id=%s | conversation_id=%s | messages=%d",
            user_id,
            conversation_id,
            len(request.messages),
        )
        return self._to_response(payload)

    def rename(
        self,
        user_id: str,
        conversation_id: str,
        request: ConversationRenameRequest,
    ) -> ConversationResponse:
        self._validate_conversation_id(conversation_id)
        owner_id = self._owner_id(user_id)
        now = datetime.now(timezone.utc)
        try:
            document = self._conversations.find_one_and_update(
                {"_id": conversation_id, "user_id": owner_id},
                {
                    "$set": {
                        "title": request.title,
                        "title_customized": True,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as exc:
            logger.exception(
                "Failed to rename conversation | user_id=%s | conversation_id=%s",
                user_id,
                conversation_id,
            )
            raise ConversationServiceError("Unable to rename conversation") from exc
        if not document:
            raise ConversationNotFoundError("Conversation was not found")
        return self._to_response(document)

    def delete(self, user_id: str, conversation_id: str) -> None:
        self._validate_conversation_id(conversation_id)
        owner_id = self._owner_id(user_id)
        try:
            result = self._conversations.delete_one(
                {"_id": conversation_id, "user_id": owner_id}
            )
        except PyMongoError as exc:
            logger.exception(
                "Failed to delete conversation | user_id=%s | conversation_id=%s",
                user_id,
                conversation_id,
            )
            raise ConversationServiceError("Unable to delete conversation") from exc
        if result.deleted_count == 1:
            logger.info(
                "Deleted conversation | user_id=%s | conversation_id=%s",
                user_id,
                conversation_id,
            )

    @staticmethod
    def _owner_id(user_id: str) -> ObjectId:
        if not ObjectId.is_valid(user_id):
            raise ConversationServiceError("Invalid authenticated user identifier")
        return ObjectId(user_id)

    @staticmethod
    def _validate_conversation_id(conversation_id: str) -> None:
        if not conversation_id or len(conversation_id) > 100:
            raise ConversationServiceError("Invalid conversation identifier")

    @staticmethod
    def _to_response(document: dict) -> ConversationResponse:
        return ConversationResponse(
            id=str(document["_id"]),
            title=document["title"],
            title_customized=document.get("title_customized", False),
            messages=document["messages"],
            created_at=document["created_at"],
            updated_at=document["updated_at"],
        )
