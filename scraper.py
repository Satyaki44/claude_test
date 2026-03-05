"""
scraper.py
Fetches GTM/PLG/RevOps posts from Hacker News (via Algolia API) and dev.to.
Both sources are fully open and work from GitHub Actions.
"""

import time
import logging
from datetime import datetime, timezone, timedelta
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HN_QUERIES = [
    "GTM engineering",
    "PLG product led growth",
    "RevOps revenue operations",
    "sales automation AI",
    "growth engineering",
    "marketing automation engineering",
    "CRM integration",
    "go to market strategy",
]

DEVTO_TAGS = [
    "gtm",
    "marketing",
    "growth",
    "salesautomation",
    "revops",
]

LOOKBACK_HOURS = 168  # 7 days


def _cutoff_ts() -> int:
    return int((datetime.now(tz=timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).timestamp())


def fetch_hn_posts(client: httpx.Client) -> list[dict]:
    posts = []
    seen: set[str] = set()
    cutoff = _cutoff_ts()

    for query in HN_QUERIES:
        log.info(f"HN search: '{query}'")
        try:
            resp = client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": query,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff}",
                    "hitsPerPage": 20,
                },
                timeout=15,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            log.info(f"  {len(hits)} hits")

            for h in hits:
                url = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
                if url in seen:
                    continue
                seen.add(url)
                posts.append({
                    "title":       h.get("title", "").strip(),
                    "author":      h.get("author", ""),
                    "publication": "Hacker News",
                    "url":         url,
                    "date":        h.get("created_at", ""),
                    "summary":     f"HN points: {h.get('points', 0)} | comments: {h.get('num_comments', 0)}",
                })
        except Exception as e:
            log.warning(f"  HN query failed: {e}")

        time.sleep(0.5)

    return posts


def fetch_devto_posts(client: httpx.Client) -> list[dict]:
    posts = []
    seen: set[str] = set()

    for tag in DEVTO_TAGS:
        log.info(f"dev.to tag: #{tag}")
        try:
            resp = client.get(
                "https://dev.to/api/articles",
                params={"tag": tag, "per_page": 20, "top": 7},
                timeout=15,
            )
            resp.raise_for_status()
            articles = resp.json()
            log.info(f"  {len(articles)} articles")

            for a in articles:
                url = a.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                posts.append({
                    "title":       a.get("title", "").strip(),
                    "author":      a.get("user", {}).get("name", ""),
                    "publication": "dev.to",
                    "url":         url,
                    "date":        a.get("published_at", ""),
                    "summary":     (a.get("description") or "")[:500],
                })
        except Exception as e:
            log.warning(f"  dev.to tag #{tag} failed: {e}")

        time.sleep(0.5)

    return posts


def fetch_posts() -> list[dict]:
    """Fetch GTM/PLG/RevOps posts from HN and dev.to."""
    with httpx.Client() as client:
        hn_posts = fetch_hn_posts(client)
        devto_posts = fetch_devto_posts(client)

    all_posts = hn_posts + devto_posts
    log.info(f"Total unique posts fetched: {len(all_posts)}")
    return all_posts
