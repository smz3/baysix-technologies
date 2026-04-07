"""
Qdrant vector store module.
Handles collection setup and document upsert for the sigma_market collection.
"""

import os
import uuid
import logging

logger = logging.getLogger(__name__)

COLLECTION = "sigma_market"
VECTOR_SIZE = 384


def get_client():
    """
    Return a QdrantClient connected to the configured Qdrant instance.
    Reads QDRANT_URL from environment (default: http://localhost:6333).
    """
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        raise RuntimeError(
            "qdrant-client not installed — run: pip install qdrant-client"
        )

    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    logger.info(f"[Qdrant] Connecting to {url}")
    return QdrantClient(url=url, timeout=30)


def ensure_collection(client) -> None:
    """
    Create the sigma_market collection if it does not already exist.
    Uses Cosine distance with 384-dimensional vectors (all-MiniLM-L6-v2).
    """
    from qdrant_client.models import Distance, VectorParams

    existing_names = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing_names:
        logger.info(f"[Qdrant] Creating collection '{COLLECTION}'...")
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"[Qdrant] Collection '{COLLECTION}' created.")
    else:
        logger.info(f"[Qdrant] Collection '{COLLECTION}' already exists.")


def upsert_documents(client, docs: list[dict]) -> int:
    """
    Upsert documents with pre-computed vectors into Qdrant.
    Each doc must have a 'vector' key (list[float], 384-dim).
    The 'vector' key is popped from the dict before storing in payload.

    Args:
        client: QdrantClient instance.
        docs:   List of document dicts with 'vector' key present.

    Returns:
        Number of points upserted.
    """
    from qdrant_client.models import PointStruct

    if not docs:
        logger.warning("[Qdrant] No documents to upsert.")
        return 0

    points = []
    for doc in docs:
        # Read vector without mutating the input doc (caller may reuse the list)
        vec = doc.get("vector", None)
        if vec is None:
            logger.warning("[Qdrant] Document missing 'vector' key — skipping.")
            continue

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "source":   doc.get("source", ""),
                    "category": doc.get("category", ""),
                    "date":     doc.get("date", ""),
                    "text":     doc.get("text", ""),
                    "url":      doc.get("url", ""),
                },
            )
        )

    if not points:
        return 0

    # Upsert in batches to stay within Qdrant's default payload limits
    BATCH_SIZE = 200
    total_upserted = 0
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION, points=batch, wait=True)
        total_upserted += len(batch)
        logger.info(f"[Qdrant] Upserted batch {i // BATCH_SIZE + 1}: {len(batch)} points")

    logger.info(f"[Qdrant] Total upserted: {total_upserted} points into '{COLLECTION}'")
    return total_upserted


def count_documents(client) -> int:
    """Return the current document count in the sigma_market collection."""
    try:
        info = client.get_collection(COLLECTION)
        return info.points_count or 0
    except Exception as e:
        logger.warning(f"[Qdrant] Could not count documents: {e}")
        return 0
