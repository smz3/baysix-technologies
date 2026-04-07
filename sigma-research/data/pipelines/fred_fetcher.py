"""
FRED data pipeline.

Fetches macroeconomic indicators from the Federal Reserve Economic Data API.
Requires FRED_API_KEY in .env (free: https://fred.stlouisfed.org/docs/api/api_key.html)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.citation_tracker import CitationStore, cite

# Load environment
load_dotenv(PROJECT_ROOT / ".env")

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "fred"

# Key macro indicators with their FRED series IDs
MACRO_SERIES = {
    "DTWEXBGS": {
        "name": "US Dollar Index (Trade Weighted)",
        "description": "Broad trade-weighted dollar index",
        "frequency": "daily",
    },
    "GS10": {
        "name": "10-Year Treasury Yield",
        "description": "Market yield on US 10-year constant maturity",
        "frequency": "daily",
    },
    "GS2": {
        "name": "2-Year Treasury Yield",
        "description": "Market yield on US 2-year constant maturity",
        "frequency": "daily",
    },
    "CPIAUCSL": {
        "name": "CPI (All Urban Consumers)",
        "description": "Consumer Price Index, seasonally adjusted",
        "frequency": "monthly",
    },
    "PAYEMS": {
        "name": "Nonfarm Payrolls (NFP)",
        "description": "Total nonfarm employment, seasonally adjusted",
        "frequency": "monthly",
    },
    "GDP": {
        "name": "GDP",
        "description": "Gross Domestic Product, seasonally adjusted annual rate",
        "frequency": "quarterly",
    },
    "M2SL": {
        "name": "M2 Money Supply",
        "description": "M2 money stock, seasonally adjusted",
        "frequency": "monthly",
    },
    "WALCL": {
        "name": "Fed Balance Sheet",
        "description": "Total assets of Federal Reserve",
        "frequency": "weekly",
    },
    "RRPONTSYD": {
        "name": "Reverse Repo (RRP)",
        "description": "Overnight reverse repurchase agreements",
        "frequency": "daily",
    },
    "TEDRATE": {
        "name": "TED Spread",
        "description": "Treasury-Eurodollar spread (credit risk indicator)",
        "frequency": "daily",
    },
    "T10Y2Y": {
        "name": "10Y-2Y Spread",
        "description": "Yield curve spread (inversion = recession signal)",
        "frequency": "daily",
    },
    "VIXCLS": {
        "name": "VIX (FRED)",
        "description": "CBOE Volatility Index from FRED",
        "frequency": "daily",
    },
}


def get_fred_client():
    """Initialize FRED API client."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print("WARNING: FRED_API_KEY not set in .env")
        print("Get a free key: https://fred.stlouisfed.org/docs/api/api_key.html")
        return None

    from fredapi import Fred

    return Fred(api_key=api_key)


def fetch_fred_series(
    series_id: str,
    start_date: str = "2020-01-01",
    fred_client=None,
) -> pd.DataFrame:
    """Fetch a single FRED series."""
    if fred_client is None:
        fred_client = get_fred_client()
    if fred_client is None:
        return pd.DataFrame()

    series = fred_client.get_series(series_id, observation_start=start_date)
    df = series.reset_index()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["value"])
    return df


def fetch_all_macro(
    start_date: str = "2020-01-01",
    save: bool = True,
    citation_store: CitationStore | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch all configured macro indicators from FRED."""
    fred = get_fred_client()
    if fred is None:
        return {}

    results = {}

    for series_id, meta in MACRO_SERIES.items():
        print(f"  Fetching {meta['name']} ({series_id})...")
        try:
            df = fetch_fred_series(series_id, start_date=start_date, fred_client=fred)

            if df.empty:
                print(f"    WARNING: No data for {series_id}")
                continue

            results[series_id] = df

            # Save to parquet
            if save:
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                filepath = RAW_DIR / f"{series_id}.parquet"
                df.to_parquet(filepath, index=False)

            # Create citation
            if citation_store is not None and not df.empty:
                latest = df.iloc[-1]
                citation_store.add(
                    cite(
                        claim=f"{meta['name']}: {latest['value']:.4f}",
                        source_name="FRED",
                        source_url=f"https://fred.stlouisfed.org/series/{series_id}",
                        data_date=str(latest["date"].date()),
                        value=float(latest["value"]),
                        confidence=1.0,  # Government data = high confidence
                    )
                )

        except Exception as e:
            print(f"    ERROR fetching {series_id}: {e}")

    return results


def get_yield_curve_spread(fred_client=None) -> float | None:
    """Quick check: 10Y-2Y spread (negative = inverted = recession signal)."""
    df = fetch_fred_series("T10Y2Y", start_date="2024-01-01", fred_client=fred_client)
    if df.empty:
        return None
    return float(df.iloc[-1]["value"])


if __name__ == "__main__":
    print("=== FRED Macro Pipeline ===\n")

    store = CitationStore()
    data = fetch_all_macro(citation_store=store)

    if not data:
        print("\nNo data fetched. Make sure FRED_API_KEY is set in .env")
        print("Get a free key: https://fred.stlouisfed.org/docs/api/api_key.html")
    else:
        print(f"\nFetched {len(data)} series successfully")
        for series_id, df in data.items():
            latest = df.iloc[-1]
            print(
                f"  {MACRO_SERIES[series_id]['name']}: {latest['value']:.4f} "
                f"({latest['date'].date()})"
            )

        print(f"\nCitations: {len(store)}")
        print(f"Parquet files saved to: {RAW_DIR}")
