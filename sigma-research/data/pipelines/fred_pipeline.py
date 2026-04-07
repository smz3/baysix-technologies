"""
FRED data pipeline — Federal Reserve Economic Data.

Requires FRED_API_KEY in .env. Gracefully falls back to last cache if key absent.
Caches to data/cache/ with 24-hour TTL (FRED data is daily).

Series fetched: CPI, yields, yield spread, M2, Fed balance sheet, payrolls, DXY.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = Path("data/cache")
CACHE_FILE = CACHE_DIR / "fred_cache.json"
CACHE_TTL_SECONDS = 86400  # 24 hours

SERIES: dict[str, str] = {
    "cpi_yoy":           "CPIAUCSL",
    "us10y_yield":       "GS10",
    "us2y_yield":        "GS2",
    "yield_spread_10y2y": "T10Y2Y",
    "m2_supply":         "M2SL",
    "fed_balance_sheet": "WALCL",
    "nonfarm_payrolls":  "PAYEMS",
    "dxy_fred":          "DTWEXBGS",
}


def fetch_fred_data() -> dict:
    """Fetch FRED macro series. Gracefully degrades to cache if key unavailable."""
    api_key = os.getenv("FRED_API_KEY", "")

    if not api_key or api_key.startswith("your_"):
        return _fallback_with_cache()

    if _cache_valid():
        print("   [fred] Serving from cache")
        return _load_cache()

    try:
        from fredapi import Fred
    except ImportError:
        return {"source": "fred_unavailable", "error": "fredapi not installed"}

    fred = Fred(api_key=api_key)
    result: dict = {"source": "fred_live"}

    for key, series_id in SERIES.items():
        try:
            series = fred.get_series(series_id).dropna()
            latest = float(series.iloc[-1])
            prev = float(series.iloc[-2]) if len(series) >= 2 else latest
            result[key] = {
                "value": round(latest, 4),
                "prev":  round(prev, 4),
                "change": round(latest - prev, 4),
            }
        except Exception as e:
            result[key] = {"error": str(e)}

    result["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
    _save_cache(result)
    return result


def _fallback_with_cache() -> dict:
    if CACHE_FILE.exists():
        data = _load_cache()
        data["source"] = "fred_cache_fallback"
        return data
    return {
        "source": "fred_unavailable",
        "error": "No FRED_API_KEY found and no cache available.",
    }


def _cache_valid() -> bool:
    if not CACHE_FILE.exists():
        return False
    try:
        data = json.loads(CACHE_FILE.read_text())
        fetched = datetime.fromisoformat(
            data.get("fetched_at_utc", "2000-01-01T00:00:00+00:00")
        )
        return (datetime.now(timezone.utc) - fetched).total_seconds() < CACHE_TTL_SECONDS
    except Exception:
        return False


def _load_cache() -> dict:
    return json.loads(CACHE_FILE.read_text())


def _save_cache(data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, indent=2))


if __name__ == "__main__":
    data = fetch_fred_data()
    print(json.dumps(data, indent=2))
