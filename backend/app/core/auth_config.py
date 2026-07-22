"""Environment-backed authentication and MongoDB configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


@dataclass(frozen=True, slots=True)
class AuthConfig:
    mongodb_uri: str
    mongodb_database: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    @classmethod
    def from_env(cls) -> "AuthConfig":
        load_dotenv(ENV_FILE, override=False)
        required = {
            "MONGODB_URI": os.getenv("MONGODB_URI", "").strip(),
            "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "").strip(),
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise RuntimeError("Missing authentication environment variables: " + ", ".join(missing))
        if len(required["JWT_SECRET_KEY"]) < 32:
            raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters")

        database = os.getenv("MONGODB_DATABASE", "jurigpt").strip()
        algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
        try:
            expiry = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        except ValueError as exc:
            raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer") from exc
        if not database or not algorithm or expiry <= 0:
            raise RuntimeError("Authentication configuration contains invalid values")
        return cls(required["MONGODB_URI"], database, required["JWT_SECRET_KEY"], algorithm, expiry)
