"""
scraper.py
Fetches posts from 10 Substack publications via free RSS feeds.
No API key required.
"""

import re
import time
import logging
import feedparser
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUBSTACK_FEEDS = [
    "https://thegtmnewsletter.substack.com/feed",         # GTMnow
    "https://gtmengineerschool.substack.com/feed",        # GTM Engineer Pulse
    "https://growthwithalex.substack.com/feed",           # Growth with Alex
    "https://buildingcreativemachines.substack.com/feed", # Building Creative Machines
    "https://startupgtm.substack.com/feed",               # StartupGTM
    "https://aimaker.substack.com/feed",                  # AI Maker
    "https://aidrivenmarketing.substack.com/feed",        # AI Driven Marketing
    "https://revengine.substack.com/feed",                # RevEngine
    "https://nathanbenaich.substack.com/feed",            # State of AI
    "https://20vc.substack.com/feed",                     # 20VC Newsletter
]


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def fetch_posts() -> list[dict]:
    """
    Fetch and deduplicate posts from all Substack feeds.
    Each post dict has: title, author, url, date, summary
    """
    posts: list[dict] = []
    seen: set[str] = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Feedfetcher/1.0; +https://github.com/Satyaki44/claude_test)"
    }

    for feed_url in SUBSTACK_FEEDS:
        log.info(f"Fetching: {feed_url}")
        try:
            resp = httpx.get(feed_url, headers=headers, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            publication = feed.feed.get("title", feed_url)

            if feed.bozo and not feed.entries:
                log.warning(f"  Failed to parse feed: {feed_url}")
                continue

            log.info(f"  {publication}: {len(feed.entries)} entries")

            for entry in feed.entries:
                url = entry.get("link", "")
                if not url or url in seen:
                    continue
                seen.add(url)

                summary = _strip_html(
                    entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
                )

                posts.append({
                    "title":       entry.get("title", "").strip(),
                    "author":      entry.get("author", publication),
                    "publication": publication,
                    "url":         url,
                    "date":        entry.get("published", ""),
                    "summary":     summary[:1000],  # cap summary length
                })

        except Exception as e:
            log.warning(f"  Error fetching {feed_url}: {e}")

        time.sleep(1)  # be polite between requests

    log.info(f"Total unique posts fetched: {len(posts)}")
    return posts
