"""MongoDB Atlas connection and collection access."""

from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, MongoClient
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
            tz_aware=True,
        )
        self._client.admin.command("ping")
        self._database = self._client[config.mongodb_database]
        self._users = self._database["users"]
        self._conversations = self._database["conversations"]
        self._generated_documents = self._database["generated_documents"]
        self._users.create_index([( "email", ASCENDING)], unique=True, name="uq_users_email")
        self._conversations.create_index(
            [("user_id", ASCENDING), ("updated_at", DESCENDING)],
            name="ix_conversations_user_updated",
        )
        self._generated_documents.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="ix_generated_documents_user_created",
        )

    @property
    def users(self) -> Collection:
        return self._users

    @property
    def conversations(self) -> Collection:
        return self._conversations

    @property
    def generated_documents(self) -> Collection:
        return self._generated_documents

    def close(self) -> None:
        self._client.close()
