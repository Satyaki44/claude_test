"""
main.py
Orchestrates: scrape → filter → summarize → save digest.
Run locally:       python main.py
Preview (no key):  python main.py --preview
Run via cron:      see .github/workflows/daily_digest.yml
"""

import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from scraper import fetch_tweets
from filter import filter_tweets
from summarizer import summarize

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
        f.write(f"# GTM Engineering Digest — {date_str}\n\n")
        f.write(text)
    return path


def print_preview(tweets: list[dict]):
    """Pretty-print filtered tweets without calling any LLM."""
    print(f"\n{'='*60}")
    print(f"  RAW FEED PREVIEW — {len(tweets)} high-signal tweets")
    print(f"{'='*60}\n")
    for i, t in enumerate(tweets, 1):
        print(f"#{i}  @{t['handle']}  |  ❤ {t['likes']}  🔁 {t['retweets']}")
        print(f"    {t['text'][:280]}")
        print(f"    {t['link']}")
        print()


def run(preview: bool = False):
    log.info("=== GTM Engineering Daily Digest ===")

    # Step 1: scrape
    raw_tweets = fetch_tweets()
    if not raw_tweets:
        log.warning("No tweets fetched — Nitter instances may be down. Exiting.")
        return

    # Step 2: filter
    filtered = filter_tweets(raw_tweets)
    if not filtered:
        log.warning("All tweets filtered out. Try lowering thresholds in filter.py.")
        return

    if preview:
        print_preview(filtered)
        return

    # Step 3: summarize
    digest = summarize(filtered)

    # Step 4: save
    path = save_digest(digest)
    log.info(f"Digest saved to: {path}")

    print("\n" + "=" * 60)
    print(digest)
    print("=" * 60)


if __name__ == "__main__":
    run(preview="--preview" in sys.argv)
