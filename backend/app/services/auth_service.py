"""User registration, authentication, and JWT operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from jwt import InvalidTokenError as JWTInvalidTokenError
from pwdlib import PasswordHash
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
    def __init__(self, users: Collection, config: AuthConfig) -> None:
        self._users = users
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
        try:
            payload = jwt.decode(
                token,
                self._config.jwt_secret_key,
                algorithms=[self._config.jwt_algorithm],
            )
            subject = payload.get("sub")
            if not isinstance(subject, str) or not ObjectId.is_valid(subject):
                raise InvalidTokenError("Invalid authentication token")
        except InvalidTokenError:
            raise
        except JWTInvalidTokenError as exc:
            raise InvalidTokenError("Invalid or expired authentication token") from exc
        except Exception as exc:
            raise InvalidTokenError("Invalid or expired authentication token") from exc

        document = self._users.find_one({"_id": ObjectId(subject), "is_active": True})
        if not document:
            raise InvalidTokenError("User account was not found")
        return AuthenticatedUser(id=subject, name=document["name"], email=document["email"])

    def _build_response(self, user_id: str, name: str, email: str) -> AuthResponse:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self._config.access_token_expire_minutes)
        token = jwt.encode(
            {"sub": user_id, "iat": now, "exp": expires_at},
            self._config.jwt_secret_key,
            algorithm=self._config.jwt_algorithm,
        )
        return AuthResponse(
            access_token=token,
            expires_in=self._config.access_token_expire_minutes * 60,
            user=AuthenticatedUser(id=user_id, name=name, email=email),
        )
