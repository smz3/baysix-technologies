"""
Yahoo Finance OHLCV ingest module.
Fetches 30 days of daily candle data for major market instruments.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

SYMBOLS = {
    "^GSPC": "SPX",
    "GC=F": "GOLD",
    "DX-Y.NYB": "DXY",
    "BTC-USD": "BTC-USD",
}


def fetch_yfinance_documents(lookback_days: int = 30) -> list[dict]:
    """
    Fetch daily OHLCV for each symbol over the last lookback_days.
    Returns a list of document dicts ready for embedding.
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed — run: pip install yfinance")
        return []

    documents = []
    end_date = datetime.today()
    start_date = end_date - timedelta(days=lookback_days + 5)  # small buffer for weekends

    for ticker_symbol, display_name in SYMBOLS.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=True,
            )

            if hist.empty:
                logger.warning(f"[yfinance] No data returned for {ticker_symbol}")
                continue

            # Trim to last lookback_days rows
            hist = hist.tail(lookback_days)

            category = "CRYPTO" if "BTC" in display_name else "EQUITY"

            for date_idx, row in hist.iterrows():
                date_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, "strftime") else str(date_idx)[:10]
                text = (
                    f"{display_name} on {date_str}: "
                    f"Open={row['Open']:.2f}, "
                    f"High={row['High']:.2f}, "
                    f"Low={row['Low']:.2f}, "
                    f"Close={row['Close']:.2f}, "
                    f"Volume={int(row['Volume'])}"
                )
                documents.append({
                    "source": "yfinance",
                    "category": category,
                    "date": date_str,
                    "text": text,
                    "url": f"https://finance.yahoo.com/quote/{ticker_symbol}",
                })

            logger.info(f"[yfinance] {display_name}: {len(hist)} candles fetched")

        except Exception as e:
            logger.warning(f"[yfinance] Failed to fetch {ticker_symbol}: {e}")
            continue

    return documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    docs = fetch_yfinance_documents()
    print(f"Fetched {len(docs)} yfinance documents")
    if docs:
        print(docs[0])
