"""
Yahoo Finance data pipeline.

Fetches cross-asset OHLCV and market data. No API key required.
Covers: SPX, VIX, Gold, DXY, bonds, sector ETFs, crypto spot prices.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.citation_tracker import CitationRecord, CitationStore, cite

# Default symbols for cross-asset monitoring
DEFAULT_SYMBOLS = {
    # Indices
    "^GSPC": "S&P 500",
    "^VIX": "VIX Volatility",
    "^DJI": "Dow Jones",
    "^IXIC": "NASDAQ",
    # Forex / DXY
    "DX-Y.NYB": "US Dollar Index (DXY)",
    # Commodities
    "GC=F": "Gold Futures",
    "SI=F": "Silver Futures",
    "CL=F": "WTI Crude Oil",
    "HG=F": "Copper Futures",
    # Bonds
    "^TNX": "10Y Treasury Yield",
    "^TYX": "30Y Treasury Yield",
    "^FVX": "5Y Treasury Yield",
    # Crypto (spot)
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    # Sector ETFs
    "XLK": "Technology ETF",
    "XLF": "Financials ETF",
    "XLE": "Energy ETF",
    "XLV": "Healthcare ETF",
    "XLI": "Industrials ETF",
}

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "yahoo"


def fetch_ohlcv(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch OHLCV data for a single symbol."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        print(f"  WARNING: No data returned for {symbol}")
        return df

    # Standardize columns
    df = df.reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Ensure date column
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    elif "datetime" in df.columns:
        df.rename(columns={"datetime": "date"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df


def fetch_multi(
    symbols: dict[str, str] | None = None,
    period: str = "1y",
    interval: str = "1d",
    save: bool = True,
    citation_store: CitationStore | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for multiple symbols. Returns dict of symbol → DataFrame."""
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    results = {}
    for symbol, name in symbols.items():
        print(f"  Fetching {name} ({symbol})...")
        df = fetch_ohlcv(symbol, period=period, interval=interval)

        if df.empty:
            continue

        results[symbol] = df

        # Save to parquet
        if save:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = symbol.replace("^", "").replace("=", "_").replace("-", "_")
            filepath = RAW_DIR / f"{safe_name}_{interval}.parquet"
            df.to_parquet(filepath, index=False)

        # Create citation
        if citation_store is not None and not df.empty:
            latest = df.iloc[-1]
            close_col = "close" if "close" in df.columns else df.columns[1]
            citation_store.add(
                cite(
                    claim=f"{name} ({symbol}) last close: {latest[close_col]:.2f}",
                    source_name="Yahoo Finance",
                    source_url=f"https://finance.yahoo.com/quote/{symbol}",
                    data_date=str(latest.get("date", "unknown")),
                    value=float(latest[close_col]),
                    confidence=0.95,
                )
            )

    return results


def fetch_latest_prices(
    symbols: dict[str, str] | None = None,
) -> dict[str, float]:
    """Quick fetch of latest closing prices only."""
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    prices = {}
    for symbol, name in symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if not hist.empty:
                prices[symbol] = float(hist["Close"].iloc[-1])
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")
    return prices


if __name__ == "__main__":
    print("=== Yahoo Finance Pipeline ===")
    print(f"Fetching {len(DEFAULT_SYMBOLS)} symbols...\n")

    store = CitationStore()
    data = fetch_multi(citation_store=store)

    print(f"\nFetched {len(data)} symbols successfully")
    for symbol, df in data.items():
        print(f"  {symbol}: {len(df)} rows, latest: {df['date'].iloc[-1]}")

    print(f"\nCitations: {len(store)}")
    print(f"Parquet files saved to: {RAW_DIR}")
