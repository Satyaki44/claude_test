"""
filter.py
Keeps only tweets that meet engagement and content quality bars.
"""

import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

# --- Thresholds (tune these freely) ------------------------------------------
MIN_LIKES     = 30
MIN_RETWEETS  = 5
MIN_LENGTH    = 80   # characters — filters one-liners and pure image posts
LOOKBACK_HOURS = 24


def _within_window(date_str: str, hours: int) -> bool:
    """Return True if the tweet date falls within the last `hours` hours."""
    if not date_str:
        return True   # no date info → don't discard
    try:
        # ntscraper returns e.g. "Mar 3, 2026 · 10:30 AM UTC"
        # Try a few common formats
        for fmt in (
            "%b %d, %Y · %I:%M %p UTC",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                dt = datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
                cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
                return dt >= cutoff
            except ValueError:
                continue
    except Exception:
        pass
    return True   # parse failed → keep tweet (conservative)


def filter_tweets(tweets: list[dict]) -> list[dict]:
    """
    Apply engagement + recency + length filters.
    Returns filtered list sorted by likes desc.
    """
    kept = []
    for t in tweets:
        reasons = []
        if t["likes"] < MIN_LIKES:
            reasons.append(f"likes={t['likes']} < {MIN_LIKES}")
        if t["retweets"] < MIN_RETWEETS:
            reasons.append(f"rt={t['retweets']} < {MIN_RETWEETS}")
        if len(t["text"]) < MIN_LENGTH:
            reasons.append(f"length={len(t['text'])} < {MIN_LENGTH}")
        if not _within_window(t["date"], LOOKBACK_HOURS):
            reasons.append("too old")

        if reasons:
            log.debug(f"Dropped ({', '.join(reasons)}): {t['link']}")
        else:
            kept.append(t)

    kept.sort(key=lambda x: x["likes"], reverse=True)
    log.info(f"Filtered: {len(tweets)} → {len(kept)} tweets kept")
    return kept
