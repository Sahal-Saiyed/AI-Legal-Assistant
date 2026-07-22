"""MongoDB Atlas connection and collection access."""

from __future__ import annotations

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.server_api import ServerApi

from backend.app.core.auth_config import AuthConfig


class MongoDatabase:
    """Own the reusable Atlas client and required indexes."""

    def __init__(self, config: AuthConfig) -> None:
        self._client: MongoClient = MongoClient(
            config.mongodb_uri,
            server_api=ServerApi("1"),
            serverSelectionTimeoutMS=10_000,
        )
        self._client.admin.command("ping")
        self._database = self._client[config.mongodb_database]
        self._users = self._database["users"]
        self._users.create_index([( "email", ASCENDING)], unique=True, name="uq_users_email")

    @property
    def users(self) -> Collection:
        return self._users

    def close(self) -> None:
        self._client.close()
