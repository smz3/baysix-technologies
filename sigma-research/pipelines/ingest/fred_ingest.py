"""
FRED API ingest module.
Fetches macro time-series data and returns structured documents.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

SERIES_CONFIG = {
    "T10Y2Y": {"label": "Yield Curve (10Y-2Y Spread)", "unit": "%"},
    "FEDFUNDS": {"label": "Federal Funds Rate", "unit": "%"},
    "CPIAUCSL": {"label": "CPI Inflation (Index)", "unit": ""},
    "DGS10": {"label": "10-Year Treasury Yield", "unit": "%"},
    "UNRATE": {"label": "Unemployment Rate", "unit": "%"},
    "VIXCLS": {"label": "VIX Close", "unit": ""},
}

LOOKBACK_DAYS = 30


def fetch_fred_documents(api_key: Optional[str] = None) -> list[dict]:
    """
    Fetch last 30 observations for each FRED series.
    Returns a list of document dicts ready for embedding.
    """
    key = api_key or os.getenv("FRED_API_KEY")
    if not key:
        logger.error("FRED_API_KEY not set — skipping FRED ingest")
        return []

    try:
        from fredapi import Fred
    except ImportError:
        logger.error("fredapi not installed — run: pip install fredapi")
        return []

    fred = Fred(api_key=key)
    documents = []
    end_date = datetime.today()
    start_date = end_date - timedelta(days=365)  # fetch wider window, trim to 30 obs

    for series_id, meta in SERIES_CONFIG.items():
        try:
            series = fred.get_series(
                series_id,
                observation_start=start_date.strftime("%Y-%m-%d"),
                observation_end=end_date.strftime("%Y-%m-%d"),
            )
            # Take last 30 non-null observations
            series = series.dropna().tail(LOOKBACK_DAYS)

            for date_idx, value in series.items():
                date_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, "strftime") else str(date_idx)[:10]
                text = f"{meta['label']}: {value:.4f}{meta['unit']} on {date_str}"
                documents.append({
                    "source": "FRED",
                    "category": "MACRO",
                    "date": date_str,
                    "text": text,
                    "url": f"https://fred.stlouisfed.org/series/{series_id}",
                })

            logger.info(f"[FRED] {series_id}: {len(series)} observations fetched")

        except Exception as e:
            logger.warning(f"[FRED] Failed to fetch {series_id}: {e}")
            continue

    return documents


if __name__ == "__main__":
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
    logging.basicConfig(level=logging.INFO)
    docs = fetch_fred_documents()
    print(f"Fetched {len(docs)} FRED documents")
    if docs:
        print(docs[0])
