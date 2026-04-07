"""
Node 1: Data Ingestion.

Pulls real market data from three sources:
  - yfinance (free, no key): SPX, VIX, DXY, BTC, Gold, yields
  - CCXT/Binance (free, no key): crypto perp prices and funding rates
  - FRED (free key required): CPI, M2, yield curve, Fed balance sheet

Gracefully degrades if any source fails. Last-known cache is served on error.
"""

import time

from data.pipelines.ccxt_pipeline import fetch_crypto_data
from data.pipelines.fred_pipeline import fetch_fred_data
from data.pipelines.yfinance_pipeline import fetch_yfinance_data
from state.trading_state import TradingState


def ingest_market_data(state: TradingState) -> dict:
    print("-> DATA INGESTION: Pulling live market data...")
    t0 = time.time()

    yf_data = fetch_yfinance_data()
    crypto_data = fetch_crypto_data()
    fred_data = fetch_fred_data()

    raw_data = {
        "yfinance": yf_data,
        "crypto": crypto_data,
        "fred": fred_data,
        "ingested_at_unix": int(time.time()),
    }

    sources_used = []
    if not yf_data.get("error"):
        sources_used.append("yfinance")
    if not crypto_data.get("error"):
        sources_used.append("ccxt_binance")
    if fred_data.get("source") not in ("fred_unavailable",):
        sources_used.append("fred")

    elapsed_ms = int((time.time() - t0) * 1000)
    print(
        f"-> DATA INGESTION: {elapsed_ms}ms | "
        f"sources={sources_used} | "
        f"fred={fred_data.get('source', 'unknown')}"
    )

    state["raw_data"] = raw_data
    state["data_sources_used"] = sources_used
    return state
