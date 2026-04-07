"""
CCXT crypto pipeline — Binance Futures data, no API key required.

Fetches: BTC/ETH/SOL — price, 24h change, funding rate.
Caches to data/cache/ with 15-min TTL.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import ccxt

CACHE_DIR = Path("data/cache")
CACHE_FILE = CACHE_DIR / "ccxt_cache.json"
CACHE_TTL_SECONDS = 900  # 15 minutes

SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]


def fetch_crypto_data() -> dict:
    """Fetch Binance perp data. Returns normalized dict."""
    if _cache_valid():
        print("   [ccxt] Serving from cache")
        return _load_cache()

    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    result: dict = {}

    try:
        tickers = exchange.fetch_tickers(SYMBOLS)
        for symbol in SYMBOLS:
            key = symbol.split("/")[0].lower()
            t = tickers.get(symbol, {})
            result[key] = {
                "price": t.get("last"),
                "change_24h_pct": round(t.get("percentage") or 0.0, 3),
                "volume_24h_usd": t.get("quoteVolume"),
            }
    except Exception as e:
        for symbol in SYMBOLS:
            key = symbol.split("/")[0].lower()
            result[key] = {"error": str(e)}

    # Funding rates (public endpoint, no key required)
    try:
        for symbol in SYMBOLS:
            key = symbol.split("/")[0].lower()
            fr = exchange.fetch_funding_rate(symbol)
            if isinstance(result.get(key), dict) and "error" not in result[key]:
                result[key]["funding_rate_pct"] = round(
                    (fr.get("fundingRate") or 0.0) * 100, 6
                )
    except Exception:
        pass

    result["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["source"] = "ccxt_binance_live"
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
    data = fetch_crypto_data()
    print(json.dumps(data, indent=2))
