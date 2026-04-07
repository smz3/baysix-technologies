"""
Crypto data pipeline.

Fetches OHLCV, funding rates, and open interest from exchanges via CCXT.
Primary exchange: Binance Futures. Fallback: Bitget.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import ccxt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.citation_tracker import CitationStore, cite

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "crypto"

# Default instruments
DEFAULT_SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]

# Default timeframes
DEFAULT_TIMEFRAMES = ["1d", "4h", "1h"]


def get_exchange(exchange_id: str = "binance") -> ccxt.Exchange:
    """Initialize exchange with rate limiting."""
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class(
        {
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        }
    )


def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    since: str | None = None,
    limit: int = 500,
    exchange: ccxt.Exchange | None = None,
) -> pd.DataFrame:
    """Fetch OHLCV candles for a single symbol/timeframe."""
    if exchange is None:
        exchange = get_exchange()

    since_ms = None
    if since:
        since_ms = exchange.parse8601(since + "T00:00:00Z")

    all_ohlcv = []
    fetch_since = since_ms

    while True:
        ohlcv = exchange.fetch_ohlcv(
            symbol, timeframe, since=fetch_since, limit=limit
        )
        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)

        # Pagination: move past last record
        fetch_since = ohlcv[-1][0] + 1

        # Stop if we've reached recent data or only got a partial page
        if len(ohlcv) < limit:
            break

        time.sleep(exchange.rateLimit / 1000.0)

    if not all_ohlcv:
        return pd.DataFrame()

    df = pd.DataFrame(
        all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    df = df.reset_index(drop=True)

    return df


def fetch_funding_rates(
    symbol: str = "BTC/USDT:USDT",
    exchange: ccxt.Exchange | None = None,
) -> pd.DataFrame:
    """Fetch recent funding rate history."""
    if exchange is None:
        exchange = get_exchange()

    try:
        funding = exchange.fetch_funding_rate_history(symbol, limit=100)
        if not funding:
            return pd.DataFrame()

        records = []
        for entry in funding:
            records.append(
                {
                    "timestamp": entry["timestamp"],
                    "date": datetime.utcfromtimestamp(entry["timestamp"] / 1000),
                    "funding_rate": entry.get("fundingRate", 0),
                    "symbol": symbol,
                }
            )
        return pd.DataFrame(records)
    except Exception as e:
        print(f"  WARNING: Funding rates not available for {symbol}: {e}")
        return pd.DataFrame()


def fetch_open_interest(
    symbol: str = "BTC/USDT:USDT",
    exchange: ccxt.Exchange | None = None,
) -> dict | None:
    """Fetch current open interest."""
    if exchange is None:
        exchange = get_exchange()

    try:
        oi = exchange.fetch_open_interest(symbol)
        return {
            "symbol": symbol,
            "open_interest": oi.get("openInterestAmount", 0),
            "open_interest_value": oi.get("openInterestValue", 0),
            "timestamp": oi.get("timestamp"),
        }
    except Exception as e:
        print(f"  WARNING: Open interest not available for {symbol}: {e}")
        return None


def fetch_all_crypto(
    symbols: list[str] | None = None,
    timeframes: list[str] | None = None,
    since: str = "2024-01-01",
    save: bool = True,
    citation_store: CitationStore | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for all symbols and timeframes."""
    if symbols is None:
        symbols = DEFAULT_SYMBOLS
    if timeframes is None:
        timeframes = DEFAULT_TIMEFRAMES

    exchange = get_exchange()
    exchange.load_markets()

    results = {}

    for symbol in symbols:
        for tf in timeframes:
            key = f"{symbol}_{tf}"
            print(f"  Fetching {symbol} {tf}...")

            try:
                df = fetch_ohlcv(
                    symbol, timeframe=tf, since=since, exchange=exchange
                )

                if df.empty:
                    continue

                results[key] = df

                # Save to parquet
                if save:
                    RAW_DIR.mkdir(parents=True, exist_ok=True)
                    safe_name = symbol.replace("/", "_").replace(":", "_")
                    filepath = RAW_DIR / f"{safe_name}_{tf}.parquet"
                    df.to_parquet(filepath, index=False)

                # Citation for daily data
                if tf == "1d" and citation_store is not None and not df.empty:
                    latest = df.iloc[-1]
                    citation_store.add(
                        cite(
                            claim=f"{symbol} close: {latest['close']:.2f}",
                            source_name="Binance Futures",
                            source_url=f"https://www.binance.com/en/futures/{symbol.split('/')[0]}USDT",
                            data_date=str(latest["date"].date()),
                            value=float(latest["close"]),
                            confidence=0.95,
                        )
                    )

            except Exception as e:
                print(f"    ERROR: {e}")

        # Funding rates (once per symbol)
        print(f"  Fetching {symbol} funding rates...")
        funding_df = fetch_funding_rates(symbol, exchange=exchange)
        if not funding_df.empty:
            results[f"{symbol}_funding"] = funding_df
            if save:
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                safe_name = symbol.replace("/", "_").replace(":", "_")
                funding_df.to_parquet(
                    RAW_DIR / f"{safe_name}_funding.parquet", index=False
                )

    return results


if __name__ == "__main__":
    print("=== Crypto Data Pipeline ===\n")

    store = CitationStore()

    # Fetch just daily for quick test
    data = fetch_all_crypto(
        symbols=["BTC/USDT:USDT"],
        timeframes=["1d"],
        since="2025-01-01",
        citation_store=store,
    )

    print(f"\nFetched {len(data)} datasets")
    for key, df in data.items():
        print(f"  {key}: {len(df)} rows")

    print(f"\nCitations: {len(store)}")
    print(f"Parquet files saved to: {RAW_DIR}")
