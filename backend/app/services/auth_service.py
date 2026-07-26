"""User registration, authentication, and JWT operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from bson import ObjectId
from jwt import InvalidTokenError as JWTInvalidTokenError
from pwdlib import PasswordHash
from pymongo import ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from backend.app.core.auth_config import AuthConfig
from backend.app.schemas.auth import AuthenticatedUser, AuthResponse


class AuthError(RuntimeError):
    pass


class EmailAlreadyRegisteredError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InvalidTokenError(AuthError):
    pass


class AuthService:
    def __init__(
        self,
        users: Collection,
        sessions: Collection,
        config: AuthConfig,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._config = config
        self._password_hash = PasswordHash.recommended()

    def register(self, name: str, email: str, password: str) -> AuthResponse:
        normalized_email = email.strip().casefold()
        now = datetime.now(timezone.utc)
        try:
            result = self._users.insert_one(
                {
                    "name": name,
                    "email": normalized_email,
                    "password_hash": self._password_hash.hash(password),
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True,
                }
            )
        except DuplicateKeyError as exc:
            raise EmailAlreadyRegisteredError("An account with this email already exists") from exc
        return self._build_response(str(result.inserted_id), name, normalized_email)

    def login(self, email: str, password: str) -> AuthResponse:
        document = self._users.find_one({"email": email.strip().casefold(), "is_active": True})
        if not document or not self._password_hash.verify(password, document["password_hash"]):
            raise InvalidCredentialsError("Incorrect email or password")
        return self._build_response(str(document["_id"]), document["name"], document["email"])

    def user_from_token(self, token: str) -> AuthenticatedUser:
        subject, session_id = self._decode_session_token(token)
        now = datetime.now(timezone.utc)
        expires_at = now + self._session_inactivity_window
        session = self._sessions.find_one_and_update(
            {
                "_id": session_id,
                "user_id": ObjectId(subject),
                "expires_at": {"$gt": now},
            },
            {
                "$set": {
                    "last_active_at": now,
                    "expires_at": expires_at,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not session:
            raise InvalidTokenError("Invalid or expired authentication session")

        document = self._users.find_one({"_id": ObjectId(subject), "is_active": True})
        if not document:
            self._sessions.delete_one({"_id": session_id})
            raise InvalidTokenError("User account was not found")
        return AuthenticatedUser(id=subject, name=document["name"], email=document["email"])

    def revoke_session(self, token: str) -> None:
        """Revoke one browser/device session without affecting other logins."""
        try:
            _, session_id = self._decode_session_token(token)
        except InvalidTokenError:
            return
        self._sessions.delete_one({"_id": session_id})

    @property
    def _session_inactivity_window(self) -> timedelta:
        return timedelta(hours=self._config.session_inactivity_hours)

    def _decode_session_token(self, token: str) -> tuple[str, str]:
        try:
            payload = jwt.decode(
                token,
                self._config.jwt_secret_key,
                algorithms=[self._config.jwt_algorithm],
                options={"require": ["sub", "sid", "iat"]},
            )
            subject = payload.get("sub")
            session_id = payload.get("sid")
            if (
                not isinstance(subject, str)
                or not ObjectId.is_valid(subject)
                or not isinstance(session_id, str)
                or not session_id
            ):
                raise InvalidTokenError("Invalid authentication token")
        except JWTInvalidTokenError as exc:
            raise InvalidTokenError("Invalid or expired authentication token") from exc
        except Exception as exc:
            raise InvalidTokenError("Invalid or expired authentication token") from exc
        return subject, session_id

    def _build_response(self, user_id: str, name: str, email: str) -> AuthResponse:
        now = datetime.now(timezone.utc)
        session_id = str(uuid4())
        expires_at = now + self._session_inactivity_window
        self._sessions.insert_one(
            {
                "_id": session_id,
                "user_id": ObjectId(user_id),
                "created_at": now,
                "last_active_at": now,
                "expires_at": expires_at,
            }
        )
        token = jwt.encode(
            {"sub": user_id, "sid": session_id, "iat": now},
            self._config.jwt_secret_key,
            algorithm=self._config.jwt_algorithm,
        )
        return AuthResponse(
            access_token=token,
            expires_in=int(self._session_inactivity_window.total_seconds()),
            user=AuthenticatedUser(id=user_id, name=name, email=email),
        )
