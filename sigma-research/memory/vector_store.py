"""
Qdrant vector store wrapper.

Provides CRUD operations for semantic search over research, citations, and alpha insights.
Connects to Qdrant at localhost:6333 (local binary, no Docker).
"""

import os
import uuid
from typing import Any, Optional

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse


class VectorStore:
    """Qdrant-backed vector store for research memory."""

    def __init__(
        self,
        collection: str = "research",
        url: str | None = None,
    ):
        self.collection = collection
        self._url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self._client = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=self._url, timeout=5)
        return self._client

    def is_available(self) -> bool:
        """Check if Qdrant is running."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def ensure_collection(self, vector_size: int = 384) -> None:
        """Create collection if it doesn't exist."""
        try:
            self.client.get_collection(self.collection)
        except (UnexpectedResponse, Exception):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            print(f"Created collection '{self.collection}' (dim={vector_size})")

    def upsert(
        self,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str:
        """Insert or update a vector with metadata."""
        point_id = doc_id or str(uuid.uuid4())
        payload = {"text": text}
        if metadata:
            payload.update(metadata)

        self.client.upsert(
            collection_name=self.collection,
            points=[
                qmodels.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
        return point_id

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Semantic search: find most similar vectors."""
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchValue(value=value),
                    )
                )
            query_filter = qmodels.Filter(must=conditions)

        results = self.client.query_points(
            collection_name=self.collection,
            query=query_embedding,
            limit=limit,
            query_filter=query_filter,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "text": point.payload.get("text", ""),
                "metadata": {
                    k: v for k, v in point.payload.items() if k != "text"
                },
            }
            for point in results.points
        ]

    def delete(self, doc_id: str) -> None:
        """Delete a vector by ID."""
        self.client.delete(
            collection_name=self.collection,
            points_selector=qmodels.PointIdsList(points=[doc_id]),
        )

    def count(self) -> int:
        """Count vectors in collection."""
        info = self.client.get_collection(self.collection)
        return info.points_count


if __name__ == "__main__":
    store = VectorStore()

    if not store.is_available():
        print("Qdrant is not running at localhost:6333")
        print("Start it first, then re-run this script.")
    else:
        print("Qdrant is available!")
        store.ensure_collection()

        # Test: import embedder and do a round-trip
        from memory.embedder import Embedder

        embedder = Embedder()

        # Upsert test documents
        docs = [
            ("DXY is strengthening, negative for gold and risk assets", {"type": "macro", "agent": "macro-researcher"}),
            ("B2B zone detected on XAUUSD H4, strong demand zone", {"type": "micro", "agent": "micro-researcher"}),
            ("SAMTC OOS test shows Sharpe 1.16 on BTC 2024-2025", {"type": "backtest", "agent": "quant-researcher"}),
        ]

        for text, meta in docs:
            vec = embedder.embed(text)
            doc_id = store.upsert(text, vec, metadata=meta)
            print(f"  Stored: {doc_id} — {text[:50]}...")

        # Search
        query = "What's the macro outlook for gold?"
        query_vec = embedder.embed(query)
        results = store.search(query_vec, limit=2)

        print(f"\nQuery: '{query}'")
        for r in results:
            print(f"  [{r['score']:.3f}] {r['text'][:60]}...")

        print(f"\nTotal vectors: {store.count()}")
