"""Persistent ChromaDB implementation of the vector-store contract."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Final

import chromadb
import numpy as np
from chromadb.api.models.Collection import Collection
from langchain_core.documents import Document

from .base import CollectionNotFoundError, VectorStore, VectorStoreValidationError

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION_NAME: Final[str] = "legal_assistant"
DEFAULT_INSERT_BATCH_SIZE: Final[int] = 500
DEFAULT_DATABASE_PATH: Final[Path] = (
    Path(__file__).resolve().parents[4] / "vector_dbs" / "chroma"
)
_METADATA_VALUE_TYPES: Final[tuple[type, ...]] = (str, int, float, bool)


class ChromaVectorStore(VectorStore):
    """Persist precomputed document embeddings in a Chroma collection."""

    def __init__(
        self,
        database_path: Path | str = DEFAULT_DATABASE_PATH,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        insert_batch_size: int = DEFAULT_INSERT_BATCH_SIZE,
    ) -> None:
        self._validate_configuration(collection_name, insert_batch_size)
        self._database_path = Path(database_path).resolve()
        self._database_path.mkdir(parents=True, exist_ok=True)
        self._collection_name = collection_name
        self._insert_batch_size = insert_batch_size
        self._client = chromadb.PersistentClient(path=str(self._database_path))
        logger.info("Using Chroma database path: %s", self._database_path)

    @property
    def database_path(self) -> Path:
        """Resolved directory containing the persistent Chroma database."""
        return self._database_path

    @property
    def collection_name(self) -> str:
        """Configured Chroma collection name."""
        return self._collection_name

    def create_collection(self) -> None:
        """Create the collection if absent, without replacing existing data."""
        already_exists = self.collection_exists()
        self._client.get_or_create_collection(name=self._collection_name)
        if already_exists:
            logger.info("Collection already exists: %s", self._collection_name)
        else:
            logger.info("Created collection: %s", self._collection_name)

    def delete_collection(self) -> None:
        """Delete the collection and log how many records were removed."""
        if not self.collection_exists():
            logger.info("Collection does not exist; nothing to delete: %s", self._collection_name)
            return

        collection = self._client.get_collection(name=self._collection_name)
        deleted_count = collection.count()
        self._client.delete_collection(name=self._collection_name)
        logger.info(
            "Deleted collection %s and %d document(s)",
            self._collection_name,
            deleted_count,
        )

    def reset_collection(self) -> None:
        """Delete any existing collection and create a fresh empty one."""
        self.delete_collection()
        self.create_collection()
        logger.info("Reset collection: %s", self._collection_name)

    def add_documents(
        self,
        documents: list[Document],
        embeddings: np.ndarray,
    ) -> None:
        """Validate and persist chunks with their externally generated vectors."""
        chunk_ids, metadatas, texts, validated_embeddings = self._validate_input(
            documents,
            embeddings,
        )
        collection = self._get_collection()
        self._validate_ids_do_not_exist(collection, chunk_ids)

        for start in range(0, len(documents), self._insert_batch_size):
            end = min(start + self._insert_batch_size, len(documents))
            try:
                collection.add(
                    ids=chunk_ids[start:end],
                    embeddings=validated_embeddings[start:end].tolist(),
                    documents=texts[start:end],
                    metadatas=metadatas[start:end],
                )
            except Exception:
                logger.exception(
                    "Failed to insert document batch [%d:%d) into collection %s",
                    start,
                    end,
                    self._collection_name,
                )
                raise
            logger.info(
                "Inserted %d document(s) into collection %s",
                end - start,
                self._collection_name,
            )

        logger.info(
            "Collection %s now contains %d vector(s)",
            self._collection_name,
            collection.count(),
        )

    def count_documents(self) -> int:
        """Return the collection count, raising when it has not been created."""
        count = self._get_collection().count()
        logger.info("Collection %s contains %d vector(s)", self._collection_name, count)
        return count

    def collection_exists(self) -> bool:
        """Check collection existence without creating it."""
        for collection in self._client.list_collections():
            name = collection if isinstance(collection, str) else collection.name
            if name == self._collection_name:
                return True
        return False

    def _get_collection(self) -> Collection:
        if not self.collection_exists():
            raise CollectionNotFoundError(
                f"Chroma collection does not exist: {self._collection_name}"
            )
        return self._client.get_collection(name=self._collection_name)

    def _validate_input(
        self,
        documents: list[Document],
        embeddings: np.ndarray,
    ) -> tuple[list[str], list[dict[str, Any]], list[str], np.ndarray]:
        if not isinstance(documents, list):
            raise TypeError("documents must be a list of LangChain Document objects")
        if not isinstance(embeddings, np.ndarray):
            raise TypeError("embeddings must be a NumPy array")
        if embeddings.ndim != 2:
            raise VectorStoreValidationError("embeddings must be a two-dimensional array")
        if not documents:
            raise VectorStoreValidationError("documents and embeddings cannot be empty")
        if embeddings.shape[0] != len(documents):
            raise VectorStoreValidationError(
                "Embedding count must equal document count "
                f"({embeddings.shape[0]} != {len(documents)})"
            )
        if embeddings.shape[1] == 0:
            raise VectorStoreValidationError("embeddings cannot have zero dimensions")
        if not np.issubdtype(embeddings.dtype, np.number):
            raise VectorStoreValidationError("embeddings must contain numeric values")

        validated_embeddings = embeddings.astype(np.float32, copy=False)
        if not np.isfinite(validated_embeddings).all():
            raise VectorStoreValidationError("embeddings must contain only finite values")

        chunk_ids: list[str] = []
        metadatas: list[dict[str, Any]] = []
        texts: list[str] = []
        for index, document in enumerate(documents):
            if not isinstance(document, Document):
                raise TypeError(f"documents[{index}] must be a LangChain Document")
            if not document.page_content.strip():
                raise VectorStoreValidationError(f"documents[{index}] has empty page content")

            chunk_id = document.metadata.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise VectorStoreValidationError(
                    f"documents[{index}] is missing a non-empty chunk_id"
                )
            self._validate_metadata(document.metadata, index)
            chunk_ids.append(chunk_id)
            metadatas.append(dict(document.metadata))
            texts.append(document.page_content)

        if len(set(chunk_ids)) != len(chunk_ids):
            raise VectorStoreValidationError("Duplicate chunk_id values found in input documents")

        return chunk_ids, metadatas, texts, validated_embeddings

    def _validate_ids_do_not_exist(self, collection: Collection, chunk_ids: list[str]) -> None:
        existing_ids: list[str] = []
        for start in range(0, len(chunk_ids), self._insert_batch_size):
            batch_ids = chunk_ids[start : start + self._insert_batch_size]
            result = collection.get(ids=batch_ids, include=[])
            existing_ids.extend(result["ids"])

        if existing_ids:
            preview = ", ".join(existing_ids[:3])
            suffix = "..." if len(existing_ids) > 3 else ""
            raise VectorStoreValidationError(
                f"Collection already contains {len(existing_ids)} supplied chunk_id value(s): "
                f"{preview}{suffix}"
            )

    @staticmethod
    def _validate_metadata(metadata: dict[str, Any], document_index: int) -> None:
        if not metadata:
            raise VectorStoreValidationError(f"documents[{document_index}] has no metadata")
        for key, value in metadata.items():
            if not isinstance(key, str) or not key:
                raise VectorStoreValidationError(
                    f"documents[{document_index}] contains an invalid metadata key"
                )
            if value is None or not isinstance(value, _METADATA_VALUE_TYPES):
                raise VectorStoreValidationError(
                    f"documents[{document_index}] metadata field {key!r} has unsupported "
                    f"type {type(value).__name__}"
                )

    @staticmethod
    def _validate_configuration(collection_name: str, insert_batch_size: int) -> None:
        if not isinstance(collection_name, str):
            raise TypeError("collection_name must be a string")
        if not collection_name.strip():
            raise ValueError("collection_name cannot be empty")
        if isinstance(insert_batch_size, bool) or not isinstance(insert_batch_size, int):
            raise TypeError("insert_batch_size must be an integer")
        if insert_batch_size <= 0:
            raise ValueError("insert_batch_size must be greater than zero")
