"""
yfinance data pipeline — real-time market data, no API key required.

Fetches: SPX, VIX, DXY, BTC, Gold, 10Y/2Y Treasury yields.
Caches to data/cache/ with 1-hour TTL to avoid rate limits.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

CACHE_DIR = Path("data/cache")
CACHE_FILE = CACHE_DIR / "yfinance_cache.json"
CACHE_TTL_SECONDS = 3600  # 1 hour

SYMBOLS: dict[str, str] = {
    "spx":   "^GSPC",
    "vix":   "^VIX",
    "dxy":   "DX-Y.NYB",
    "btc":   "BTC-USD",
    "gold":  "GC=F",
    "us10y": "^TNX",
    "us2y":  "^FVX",
}


def fetch_yfinance_data() -> dict:
    """Fetch latest prices for key market indicators. Returns normalized dict."""
    if _cache_valid():
        print("   [yfinance] Serving from cache")
        return _load_cache()

    result: dict = {}
    for key, ticker in SYMBOLS.items():
        try:
            data = yf.download(
                ticker, period="5d", interval="1d", progress=False, auto_adjust=True
            )
            if data.empty:
                result[key] = {"error": "no_data"}
                continue
            close = data["Close"].dropna()
            latest = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) >= 2 else latest
            result[key] = {
                "price": round(latest, 4),
                "change_1d_pct": round((latest / prev - 1) * 100, 3),
            }
        except Exception as e:
            result[key] = {"error": str(e)}

    result["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["source"] = "yfinance_live"
    _save_cache(result)
    return result


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
    data = fetch_yfinance_data()
    print(json.dumps(data, indent=2))
