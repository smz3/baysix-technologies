"""
CCXT Binance futures ingest module.
Fetches 24h ticker data for major crypto perpetual futures.
Falls back to spot market if futures symbol is unavailable.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

FUTURES_SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
SPOT_FALLBACK = {
    "BTC/USDT:USDT": "BTC/USDT",
    "ETH/USDT:USDT": "ETH/USDT",
    "SOL/USDT:USDT": "SOL/USDT",
}


def _build_document(symbol: str, ticker: dict, market_type: str) -> dict:
    """Build a document dict from a ccxt ticker response."""
    last = ticker.get("last") or 0.0
    percentage = ticker.get("percentage") or 0.0
    quote_volume = ticker.get("quoteVolume") or 0.0
    high = ticker.get("high") or 0.0
    low = ticker.get("low") or 0.0
    bid = ticker.get("bid") or 0.0
    ask = ticker.get("ask") or 0.0

    market_label = "Futures" if market_type == "futures" else "Spot"
    display_symbol = symbol.replace(":USDT", "") if ":USDT" in symbol else symbol

    text = (
        f"{display_symbol} 24h [{market_label}]: "
        f"Last={last:.2f}, "
        f"Change={percentage:.2f}%, "
        f"Volume={quote_volume:.0f} USDT, "
        f"High={high:.2f}, "
        f"Low={low:.2f}, "
        f"Bid={bid:.2f}, "
        f"Ask={ask:.2f}"
    )

    return {
        "source": "Binance",
        "category": "CRYPTO",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "text": text,
        "url": "https://www.binance.com/en/futures",
    }


def fetch_ccxt_documents() -> list[dict]:
    """
    Fetch 24h ticker data from Binance futures (public endpoint, no API key).
    Falls back to spot market if a futures symbol is unavailable.
    Returns a list of document dicts ready for embedding.
    """
    try:
        import ccxt
    except ImportError:
        logger.error("ccxt not installed — run: pip install ccxt")
        return []

    documents = []

    # Primary: Binance USD-M futures
    try:
        futures_exchange = ccxt.binanceusdm({
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })
        futures_exchange.load_markets()
    except Exception as e:
        logger.warning(f"[CCXT] Failed to init Binance futures exchange: {e}")
        futures_exchange = None

    # Fallback: Binance spot
    try:
        spot_exchange = ccxt.binance({
            "enableRateLimit": True,
        })
        spot_exchange.load_markets()
    except Exception as e:
        logger.warning(f"[CCXT] Failed to init Binance spot exchange: {e}")
        spot_exchange = None

    for futures_symbol in FUTURES_SYMBOLS:
        fetched = False

        # Try futures first
        if futures_exchange is not None:
            try:
                ticker = futures_exchange.fetch_ticker(futures_symbol)
                doc = _build_document(futures_symbol, ticker, "futures")
                documents.append(doc)
                logger.info(f"[CCXT] Fetched futures ticker: {futures_symbol}")
                fetched = True
            except Exception as e:
                logger.warning(f"[CCXT] Futures fetch failed for {futures_symbol}: {e} — trying spot fallback")

        # Fallback to spot
        if not fetched and spot_exchange is not None:
            spot_symbol = SPOT_FALLBACK.get(futures_symbol, futures_symbol.replace(":USDT", ""))
            try:
                ticker = spot_exchange.fetch_ticker(spot_symbol)
                doc = _build_document(spot_symbol, ticker, "spot")
                documents.append(doc)
                logger.info(f"[CCXT] Fetched spot ticker: {spot_symbol} (fallback)")
                fetched = True
            except Exception as e:
                logger.warning(f"[CCXT] Spot fallback also failed for {spot_symbol}: {e}")

        if not fetched:
            logger.error(f"[CCXT] Could not fetch any data for {futures_symbol}")

    return documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    docs = fetch_ccxt_documents()
    print(f"Fetched {len(docs)} CCXT documents")
    for d in docs:
        print(d["text"])
