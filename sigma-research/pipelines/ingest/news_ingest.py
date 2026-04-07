"""
RSS news ingest module.
Fetches and parses financial/crypto news headlines into documents.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "category": "CRYPTO",
    },
    {
        "name": "CoinTelegraph",
        "url": "https://cointelegraph.com/rss",
        "category": "CRYPTO",
    },
    {
        "name": "CNBC Economy",
        "url": "https://www.cnbc.com/id/15839056/device/rss/rss.xml",
        "category": "NEWS",
    },
    {
        "name": "MarketWatch",
        "url": "https://www.marketwatch.com/rss/economy",
        "category": "NEWS",
    },
]

MAX_ARTICLES_PER_FEED = 10


def _parse_entry_date(entry) -> str:
    """Extract and normalise the publication date from a feedparser entry."""
    # Try structured time first
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                import time as _time
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass

    # Fallback: raw string, take first 10 chars (YYYY-MM-DD)
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw and len(raw) >= 10:
            return raw[:10]

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _clean_html(text: Optional[str]) -> str:
    """Strip basic HTML tags from a string."""
    if not text:
        return ""
    import re
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def fetch_news_documents() -> list[dict]:
    """
    Parse RSS feeds and return structured document dicts.
    Returns a list of document dicts ready for embedding.
    """
    try:
        import feedparser
    except ImportError:
        logger.error("feedparser not installed — run: pip install feedparser")
        return []

    documents = []

    for feed_config in RSS_FEEDS:
        feed_name = feed_config["name"]
        feed_url = feed_config["url"]
        category = feed_config["category"]

        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.warning(f"[News] Feed parse error for {feed_name}: {feed.bozo_exception}")
                continue

            entries = feed.entries[:MAX_ARTICLES_PER_FEED]
            count = 0

            for entry in entries:
                title = _clean_html(getattr(entry, "title", "")).strip()
                if not title:
                    continue

                # Description: prefer summary, fallback to content
                raw_desc = getattr(entry, "summary", "") or ""
                if not raw_desc:
                    content_list = getattr(entry, "content", [])
                    if content_list:
                        raw_desc = content_list[0].get("value", "")
                description = _clean_html(raw_desc)[:200]

                url = getattr(entry, "link", "")
                date_str = _parse_entry_date(entry)

                text = f"{title}. {description}" if description else title

                documents.append({
                    "source": feed_name,
                    "category": category,
                    "date": date_str,
                    "text": text,
                    "url": url,
                })
                count += 1

            logger.info(f"[News] {feed_name}: {count} articles fetched")

        except Exception as e:
            logger.warning(f"[News] Failed to fetch feed {feed_name} ({feed_url}): {e}")
            continue

    return documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    docs = fetch_news_documents()
    print(f"Fetched {len(docs)} news documents")
    if docs:
        print(docs[0])
