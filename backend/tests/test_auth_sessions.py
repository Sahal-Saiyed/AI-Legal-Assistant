"""Unit tests for persistent sliding authentication sessions."""

from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from bson import ObjectId

from backend.app.core.auth_config import AuthConfig
from backend.app.services.auth_service import AuthService, InvalidTokenError


class MemoryCollection:
    def __init__(self, documents: list[dict[str, Any]] | None = None) -> None:
        self.documents = {
            document["_id"]: deepcopy(document)
            for document in (documents or [])
        }

    def insert_one(self, document: dict[str, Any]) -> SimpleNamespace:
        stored = deepcopy(document)
        stored.setdefault("_id", ObjectId())
        self.documents[stored["_id"]] = stored
        return SimpleNamespace(inserted_id=stored["_id"])

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for document in self.documents.values():
            if all(document.get(key) == value for key, value in query.items()):
                return deepcopy(document)
        return None

    def find_one_and_update(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        **_: Any,
    ) -> dict[str, Any] | None:
        document = self.documents.get(query.get("_id"))
        if not document or document.get("user_id") != query.get("user_id"):
            return None
        expiry_query = query.get("expires_at", {})
        if document["expires_at"] <= expiry_query.get("$gt"):
            return None
        document.update(deepcopy(update["$set"]))
        return deepcopy(document)

    def delete_one(self, query: dict[str, Any]) -> SimpleNamespace:
        deleted = int(self.documents.pop(query.get("_id"), None) is not None)
        return SimpleNamespace(deleted_count=deleted)


class SlidingSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = ObjectId()
        self.users = MemoryCollection(
            [
                {
                    "_id": self.user_id,
                    "name": "Session User",
                    "email": "session@example.com",
                    "is_active": True,
                }
            ]
        )
        self.sessions = MemoryCollection()
        self.service = AuthService(
            self.users,  # type: ignore[arg-type]
            self.sessions,  # type: ignore[arg-type]
            AuthConfig(
                mongodb_uri="mongodb://example",
                mongodb_database="jurigpt",
                jwt_secret_key="x" * 32,
                jwt_algorithm="HS256",
                session_inactivity_hours=48,
            ),
        )

    def test_session_is_created_for_48_hours_and_renews(self) -> None:
        response = self.service._build_response(  # noqa: SLF001
            str(self.user_id),
            "Session User",
            "session@example.com",
        )
        self.assertEqual(response.expires_in, 48 * 60 * 60)
        session = next(iter(self.sessions.documents.values()))
        initial_expiry = session["expires_at"]

        session["expires_at"] = datetime.now(timezone.utc) + timedelta(hours=1)
        user = self.service.user_from_token(response.access_token)

        self.assertEqual(user.id, str(self.user_id))
        self.assertGreater(session["expires_at"], initial_expiry - timedelta(minutes=1))
        self.assertGreater(
            session["expires_at"],
            datetime.now(timezone.utc) + timedelta(hours=47, minutes=59),
        )

    def test_expired_session_is_rejected(self) -> None:
        response = self.service._build_response(  # noqa: SLF001
            str(self.user_id),
            "Session User",
            "session@example.com",
        )
        session = next(iter(self.sessions.documents.values()))
        session["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)

        with self.assertRaises(InvalidTokenError):
            self.service.user_from_token(response.access_token)

    def test_logout_revokes_only_the_current_session(self) -> None:
        first = self.service._build_response(  # noqa: SLF001
            str(self.user_id),
            "Session User",
            "session@example.com",
        )
        second = self.service._build_response(  # noqa: SLF001
            str(self.user_id),
            "Session User",
            "session@example.com",
        )

        self.service.revoke_session(first.access_token)

        with self.assertRaises(InvalidTokenError):
            self.service.user_from_token(first.access_token)
        self.assertEqual(
            self.service.user_from_token(second.access_token).id,
            str(self.user_id),
        )
