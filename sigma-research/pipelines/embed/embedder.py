"""
Embedding module using sentence-transformers.
Lazy-loads the model on first use (all-MiniLM-L6-v2, 384-dim).
"""

import logging

logger = logging.getLogger(__name__)

_model = None


def get_model():
    """Return the singleton SentenceTransformer model, loading it on first call."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[Embedder] Loading all-MiniLM-L6-v2 model...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[Embedder] Model loaded.")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed — run: pip install sentence-transformers"
            )
    return _model


def embed_documents(docs: list[dict]) -> list[dict]:
    """
    Add a 'vector' key (list[float], 384-dim) to each document dict.
    Documents are mutated in place and also returned.

    Args:
        docs: List of document dicts, each must have a 'text' key.

    Returns:
        The same list with 'vector' added to each dict.
    """
    if not docs:
        logger.warning("[Embedder] No documents to embed.")
        return docs

    model = get_model()
    texts = [d["text"] for d in docs]

    logger.info(f"[Embedder] Embedding {len(texts)} documents...")
    vectors = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=32,
        convert_to_numpy=True,
    )

    for doc, vec in zip(docs, vectors):
        doc["vector"] = vec.tolist()

    logger.info(f"[Embedder] Done. Vector shape: {vectors.shape}")
    return docs
