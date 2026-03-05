"""
filter.py
Filters Substack posts by recency. Keeps posts from the last LOOKBACK_HOURS.
"""

import logging
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional

log = logging.getLogger(__name__)

LOOKBACK_HOURS = 168  # 7 days


def _parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse RSS date strings into timezone-aware datetimes.
    Handles RFC 2822 format (standard RSS): "Wed, 05 Mar 2026 10:00:00 +0000"
    Falls back to common ISO formats.
    """
    if not date_str:
        return None

    # Try RFC 2822 first (standard RSS pubDate format)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass

    # Fallback: try ISO formats
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    return None


def _within_window(date_str: str, hours: int) -> bool:
    """Return True if the post date falls within the last `hours` hours."""
    dt = _parse_date(date_str)
    if dt is None:
        return True  # can't parse → keep it (conservative)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    return dt >= cutoff


def filter_posts(posts: list[dict]) -> list[dict]:
    """
    Keep only posts from the last LOOKBACK_HOURS, sorted by date desc.
    """
    kept = []
    for post in posts:
        if _within_window(post["date"], LOOKBACK_HOURS):
            kept.append(post)
        else:
            log.debug(f"Dropped (too old): {post['url']}")

    # Sort newest first
    def sort_key(p):
        dt = _parse_date(p["date"])
        return dt if dt else datetime.min.replace(tzinfo=timezone.utc)

    kept.sort(key=sort_key, reverse=True)
    log.info(f"Filtered: {len(posts)} → {len(kept)} posts kept (last {LOOKBACK_HOURS}h)")
    return kept
