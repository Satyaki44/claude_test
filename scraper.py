"""
scraper.py
Searches Nitter (via ntscraper) for high-signal GTM + engineering tweets.
No API key needed — fully free.
"""

import time
import logging
from ntscraper import Nitter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# --- Search queries -----------------------------------------------------------
QUERIES = [
    "GTM engineering",
    "go-to-market engineering",
    "developer-led growth engineering",
    "PLG engineering",
    "RevOps engineering",
    "sales engineering growth",
]

TWEETS_PER_QUERY = 50   # fetch this many, filter down after
LOOKBACK_HOURS   = 24   # only keep tweets from the last N hours


def _parse_count(raw) -> int:
    """Ntscraper returns counts as ints or strings like '1.2K'. Normalise."""
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        raw = raw.strip().upper()
        if raw.endswith("K"):
            return int(float(raw[:-1]) * 1_000)
        if raw.endswith("M"):
            return int(float(raw[:-1]) * 1_000_000)
        try:
            return int(raw)
        except ValueError:
            return 0
    return 0


def fetch_tweets() -> list[dict]:
    """
    Run all queries against Nitter and return a deduplicated list of raw tweets.
    Each tweet dict has at minimum:
        text, link, date, likes, retweets, author
    """
    scraper = Nitter(log_level=1, skip_instance_check=False)
    seen_links: set[str] = set()
    results: list[dict] = []

    for query in QUERIES:
        log.info(f"Searching: '{query}'")
        try:
            data = scraper.get_tweets(query, mode="term", number=TWEETS_PER_QUERY)
        except Exception as e:
            log.warning(f"Query '{query}' failed: {e}")
            time.sleep(2)
            continue

        tweets = data.get("tweets", [])
        log.info(f"  → {len(tweets)} raw results")

        for t in tweets:
            link = t.get("link", "")
            if not link or link in seen_links:
                continue
            seen_links.add(link)

            results.append({
                "text":     t.get("text", "").strip(),
                "link":     link,
                "date":     t.get("date", ""),
                "likes":    _parse_count(t.get("likes", 0)),
                "retweets": _parse_count(t.get("retweets", 0)),
                "author":   t.get("user", {}).get("name", ""),
                "handle":   t.get("user", {}).get("username", ""),
            })

        time.sleep(1)   # be polite between queries

    log.info(f"Total unique tweets fetched: {len(results)}")
    return results
