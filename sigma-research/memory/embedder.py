"""
Local embedding engine using sentence-transformers.

Model: all-MiniLM-L6-v2 (80MB, 384 dimensions, ~10ms/embed on CPU)
No API cost. No external calls. Fully local.
"""

from sentence_transformers import SentenceTransformer


class Embedder:
    """Local text embedding using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None  # Lazy load

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            print(f"Loading embedding model: {self._model_name}...")
            self._model = SentenceTransformer(self._model_name)
            print(f"Model loaded. Dimension: {self.dimension}")
        return self._model

    @property
    def dimension(self) -> int:
        """Embedding vector dimension (384 for MiniLM)."""
        return self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        vectors = self.model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        return vectors.tolist()


if __name__ == "__main__":
    embedder = Embedder()

    # Test single embed
    text = "XAUUSD is showing a B2B zone formation on the H4 timeframe"
    vector = embedder.embed(text)
    print(f"Text: {text}")
    print(f"Dimension: {len(vector)}")
    print(f"First 5 values: {vector[:5]}")

    # Test batch
    texts = [
        "DXY strengthening, bearish for gold",
        "Risk-off regime, flight to safety",
        "SAMTC signal detected on BTC daily",
    ]
    vectors = embedder.embed_batch(texts)
    print(f"\nBatch embedded {len(vectors)} texts, each {len(vectors[0])} dims")
