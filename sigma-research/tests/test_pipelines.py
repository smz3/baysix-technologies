"""
Smoke tests for sigma-research foundation.

These tests verify that core modules work correctly.
Infrastructure-dependent tests (Qdrant, Ollama) are skipped if services unavailable.
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# --- Citation Tracker ---


class TestCitationTracker:
    def test_create_citation(self):
        from memory.citation_tracker import CitationRecord

        c = CitationRecord(
            claim="DXY at 104.2",
            source_name="FRED",
            source_url="https://fred.stlouisfed.org/series/DTWEXBGS",
            data_date="2026-03-25",
            value=104.2,
        )
        assert c.claim == "DXY at 104.2"
        assert c.confidence == 1.0
        assert c.verified_by == []
        assert len(c.id) == 8

    def test_citation_store_crud(self):
        from memory.citation_tracker import CitationStore, cite

        store = CitationStore()
        c1 = cite("DXY at 104", "FRED", "http://fred.example", "2026-03-25", 104.0)
        c2 = cite("VIX at 18", "Yahoo", "http://yahoo.example", "2026-03-25", 18.0)

        store.add(c1)
        store.add(c2)

        assert len(store) == 2
        assert store.get(c1.id) is not None
        assert len(store.get_by_source("FRED")) == 1
        assert len(store.get_by_claim("dxy")) == 1  # case insensitive

    def test_citation_verify(self):
        from memory.citation_tracker import CitationStore, cite

        store = CitationStore()
        c = cite("test claim", "test", "http://test", "2026-01-01", 1.0)
        store.add(c)
        store.verify(c.id, "macro-researcher")
        store.verify(c.id, "mathematician")

        assert store.get(c.id).verified_by == ["macro-researcher", "mathematician"]

    def test_citation_markdown(self):
        from memory.citation_tracker import CitationStore, cite

        store = CitationStore()
        store.add(cite("test", "FRED", "http://fred", "2026-01-01", 1.0))
        md = store.to_markdown()
        assert "## Sources" in md
        assert "FRED" in md

    def test_citation_persistence(self, tmp_path):
        from memory.citation_tracker import CitationStore, cite

        path = tmp_path / "citations.json"
        store = CitationStore(persist_path=path)
        store.add(cite("test", "FRED", "http://fred", "2026-01-01", 1.0))
        store.save()

        store2 = CitationStore(persist_path=path)
        store2.load()
        assert len(store2) == 1


# --- Yahoo Finance ---


class TestYahooFinance:
    def test_fetch_single_symbol(self):
        from data.pipelines.yahoo_finance import fetch_ohlcv

        df = fetch_ohlcv("^GSPC", period="5d", interval="1d")
        assert not df.empty
        assert "close" in df.columns
        assert "date" in df.columns
        assert len(df) >= 1

    def test_fetch_gold(self):
        from data.pipelines.yahoo_finance import fetch_ohlcv

        df = fetch_ohlcv("GC=F", period="5d", interval="1d")
        assert not df.empty
        assert "close" in df.columns

    def test_fetch_multi(self):
        from data.pipelines.yahoo_finance import fetch_multi

        symbols = {"^GSPC": "S&P 500", "GC=F": "Gold"}
        data = fetch_multi(symbols=symbols, period="5d", save=False)
        assert len(data) >= 1

    def test_latest_prices(self):
        from data.pipelines.yahoo_finance import fetch_latest_prices

        prices = fetch_latest_prices(symbols={"^GSPC": "S&P 500"})
        assert "^GSPC" in prices
        assert prices["^GSPC"] > 0


# --- FRED (skipped if no API key) ---


class TestFRED:
    @pytest.fixture(autouse=True)
    def check_fred_key(self):
        import os
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
        if not os.getenv("FRED_API_KEY"):
            pytest.skip("FRED_API_KEY not set")

    def test_fetch_single_series(self):
        from data.pipelines.fred_fetcher import fetch_fred_series

        df = fetch_fred_series("GS10", start_date="2025-01-01")
        assert not df.empty
        assert "value" in df.columns

    def test_fetch_all_macro(self):
        from data.pipelines.fred_fetcher import fetch_all_macro

        data = fetch_all_macro(start_date="2025-01-01", save=False)
        assert len(data) >= 1


# --- Embedder ---


class TestEmbedder:
    def test_embed_single(self):
        from memory.embedder import Embedder

        embedder = Embedder()
        vec = embedder.embed("test text")
        assert len(vec) == 384
        assert isinstance(vec[0], float)

    def test_embed_batch(self):
        from memory.embedder import Embedder

        embedder = Embedder()
        vecs = embedder.embed_batch(["text one", "text two"])
        assert len(vecs) == 2
        assert len(vecs[0]) == 384

    def test_dimension_property(self):
        from memory.embedder import Embedder

        embedder = Embedder()
        assert embedder.dimension == 384


# --- Vector Store (skipped if Qdrant not running) ---


class TestVectorStore:
    @pytest.fixture(autouse=True)
    def check_qdrant(self):
        from memory.vector_store import VectorStore

        store = VectorStore(collection="test_research")
        if not store.is_available():
            pytest.skip("Qdrant not running at localhost:6333")
        self.store = store
        self.store.ensure_collection()

    def test_upsert_and_search(self):
        from memory.embedder import Embedder

        embedder = Embedder()
        vec = embedder.embed("gold is a safe haven asset")
        self.store.upsert("gold is a safe haven asset", vec, {"type": "macro"})

        query_vec = embedder.embed("what about gold?")
        results = self.store.search(query_vec, limit=1)
        assert len(results) >= 1
        assert "gold" in results[0]["text"].lower()


# --- Ollama (skipped if not running) ---


class TestOllama:
    @pytest.fixture(autouse=True)
    def check_ollama(self):
        from llm.ollama_client import OllamaClient

        client = OllamaClient()
        if not client.is_available():
            pytest.skip("Ollama not running at localhost:11434")
        self.client = client

    def test_list_models(self):
        models = self.client.list_models()
        assert isinstance(models, list)

    def test_sentiment_classification(self):
        models = self.client.list_models()
        if not any("qwen" in m for m in models):
            pytest.skip("qwen2.5:7b not pulled")

        result = self.client.classify_sentiment("Gold surges to record high on Fed pivot")
        assert "sentiment" in result
        assert result["sentiment"] in ["bullish", "bearish", "neutral"]
