"""
Sigma-Quant Intelligence Centre — Data Pipeline Orchestrator
============================================================
Runs all ingest modules, embeds documents, and upserts into Qdrant.

Usage:
    # From sigma-research root:
    python pipelines/run_pipeline.py

    # As a module:
    python -m pipelines.run_pipeline
"""

import logging
import os
import sys
import time

# ---------------------------------------------------------------------------
# Resolve and load .env before any other imports that may read env vars
# ---------------------------------------------------------------------------
from dotenv import load_dotenv, find_dotenv

_env_path = find_dotenv(
    filename=".env",
    raise_error_if_not_found=False,
    usecwd=True,
)
if not _env_path:
    # Explicit fallback to the known sigma-research root
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")

load_dotenv(_env_path, override=False)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("run_pipeline")


def run_ingest_stage() -> dict[str, list[dict]]:
    """Run all ingest modules. Returns mapping of source_name -> docs list."""
    from pipelines.ingest.fred_ingest import fetch_fred_documents
    from pipelines.ingest.yfinance_ingest import fetch_yfinance_documents
    from pipelines.ingest.ccxt_ingest import fetch_ccxt_documents
    from pipelines.ingest.news_ingest import fetch_news_documents

    stages = [
        ("FRED",     fetch_fred_documents),
        ("yfinance", fetch_yfinance_documents),
        ("Binance",  fetch_ccxt_documents),
        ("News",     fetch_news_documents),
    ]

    results: dict[str, list[dict]] = {}
    for name, fn in stages:
        logger.info(f"--- Running ingest: {name} ---")
        t0 = time.time()
        try:
            docs = fn()
        except Exception as e:
            logger.error(f"[{name}] Ingest raised an exception: {e}", exc_info=True)
            docs = []
        elapsed = time.time() - t0
        logger.info(f"[{name}] {len(docs)} docs in {elapsed:.1f}s")
        results[name] = docs

    return results


def print_summary(results: dict[str, list[dict]], total_upserted: int) -> None:
    """Print a clean pipeline summary table."""
    print("\n" + "=" * 55)
    print("  SIGMA-QUANT PIPELINE SUMMARY")
    print("=" * 55)
    grand_total = 0
    for source, docs in results.items():
        print(f"  [{source:<10}] {len(docs):>5} docs")
        grand_total += len(docs)
    print("-" * 55)
    print(f"  {'Total':>12}  {grand_total:>5} docs -> embedded -> {total_upserted} points upserted to sigma_market")
    print("=" * 55 + "\n")


def main() -> None:
    logger.info("=== Sigma-Quant Intelligence Centre Pipeline START ===")

    # 1. Ingest
    results = run_ingest_stage()

    # Flatten all docs
    all_docs: list[dict] = []
    for docs in results.values():
        all_docs.extend(docs)

    if not all_docs:
        logger.error("No documents collected from any source. Aborting.")
        sys.exit(1)

    logger.info(f"Total documents collected: {len(all_docs)}")

    # 2. Embed
    logger.info("--- Embedding documents ---")
    from pipelines.embed.embedder import embed_documents
    try:
        all_docs = embed_documents(all_docs)
    except Exception as e:
        logger.error(f"Embedding failed: {e}", exc_info=True)
        sys.exit(1)

    # 3. Qdrant upsert
    logger.info("--- Connecting to Qdrant ---")
    from pipelines.store.qdrant_store import get_client, ensure_collection, upsert_documents
    try:
        client = get_client()
        ensure_collection(client)
        total_upserted = upsert_documents(client, all_docs)
    except Exception as e:
        logger.error(f"Qdrant upsert failed: {e}", exc_info=True)
        sys.exit(1)

    # 4. Print summary
    print_summary(results, total_upserted)
    logger.info("=== Pipeline COMPLETE ===")


if __name__ == "__main__":
    main()
