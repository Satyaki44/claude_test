"""
main.py
Orchestrates: scrape → filter → summarize → publish to Telegram → save digest.

Run locally:       python main.py
Preview (no keys): python main.py --preview
Run via cron:      see .github/workflows/daily_digest.yml
"""

import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from scraper import fetch_posts
from filter import filter_posts
from summarizer import summarize
from telegram import publish

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

DIGESTS_DIR = "digests"


def save_digest(text: str) -> str:
    os.makedirs(DIGESTS_DIR, exist_ok=True)
    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(DIGESTS_DIR, f"{date_str}.md")
    with open(path, "w") as f:
        f.write(f"# AI x Marketing Digest — {date_str}\n\n")
        f.write(text)
    return path


def print_preview(posts: list[dict]):
    """Pretty-print filtered posts without calling any LLM or Telegram."""
    print(f"\n{'='*60}")
    print(f"  RAW FEED PREVIEW — {len(posts)} posts from last 24h")
    print(f"{'='*60}\n")
    for i, p in enumerate(posts, 1):
        print(f"#{i}  [{p['publication']}]")
        print(f"    {p['title']}")
        print(f"    {p['date']}")
        print(f"    {p['summary'][:200]}...")
        print(f"    {p['url']}")
        print()


def run(preview: bool = False):
    log.info("=== GTM x AI Twitter Post Generator ===")

    # Step 1: scrape
    raw_posts = fetch_posts()
    if not raw_posts:
        log.warning("No posts fetched. Check feed URLs or network. Exiting.")
        return

    # Step 2: filter
    filtered = filter_posts(raw_posts)
    if not filtered:
        log.warning("No posts from the last 7 days. Try widening LOOKBACK_HOURS in filter.py.")
        return

    if preview:
        print_preview(filtered)
        return

    # Step 3: summarize
    digest = summarize(filtered)

    # Step 4: publish to Telegram
    try:
        success = publish(digest)
        if success:
            log.info("Digest published to Telegram.")
        else:
            log.warning("Telegram publish failed — digest still saved locally.")
    except EnvironmentError as e:
        log.warning(f"Telegram skipped: {e}")

    # Step 5: save locally
    path = save_digest(digest)
    log.info(f"Digest saved to: {path}")

    print("\n" + "=" * 60)
    print(digest)
    print("=" * 60)


if __name__ == "__main__":
    run(preview="--preview" in sys.argv)
