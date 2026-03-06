"""
main.py
Orchestrates: feedback poll → scrape → filter → discover → synthesize → publish → save.

Run locally:       python3 main.py
Preview (no LLM):  python3 main.py --preview
Run via cron:      render.yaml
"""

import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from scraper import fetch_posts
from filter import filter_posts
from discoverer import find_bridge_pairs
from summarizer import synthesize
from feedback import poll_and_process_feedback
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


def print_preview(posts: list[dict], pairs: list[dict]):
    """Print filtered posts and discovered bridge pairs. No LLM or Telegram calls."""
    print(f"\n{'='*60}")
    print(f"  FEED PREVIEW — {len(posts)} posts from last 7 days")
    print(f"{'='*60}\n")
    for i, p in enumerate(posts, 1):
        print(f"#{i}  [{p['publication']}]")
        print(f"    {p['title']}")
        print(f"    {p['url']}")
        print()

    if pairs:
        print(f"\n{'='*60}")
        print(f"  BRIDGE PAIRS — {len(pairs)} pairs in goldilocks zone")
        print(f"{'='*60}\n")
        for i, pair in enumerate(pairs, 1):
            a, b = pair["post_a"], pair["post_b"]
            print(f"PAIR {i}  (similarity: {pair['similarity']:.3f})")
            print(f"  A: [{a['publication']}] {a['title']}")
            print(f"  B: [{b['publication']}] {b['title']}")
            print()
    else:
        print("\n  No bridge pairs found. Try widening SIMILARITY_LOW/HIGH in discoverer.py\n")
        print("  or extending LOOKBACK_HOURS in filter.py to get more posts.\n")


def run(preview: bool = False):
    log.info("=== GTM x AI Digest ===")

    # Step 0: poll for 👍/👎 feedback from yesterday's messages
    preferences = {}
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token and not preview:
        try:
            preferences = poll_and_process_feedback(token)
        except Exception as e:
            log.warning(f"Feedback poll failed (non-fatal): {e}")

    # Step 1: scrape
    raw_posts = fetch_posts()
    if not raw_posts:
        log.warning("No posts fetched. Check feed URLs or network. Exiting.")
        return

    # Step 2: filter (last 7 days)
    filtered = filter_posts(raw_posts)
    if not filtered:
        log.warning("No posts from the last 7 days. Try widening LOOKBACK_HOURS in filter.py.")
        return

    # Step 3: LBD — find bridge pairs across publications
    if len(filtered) < 2:
        log.warning("Only 1 post after filtering — LBD needs at least 2. Exiting.")
        return

    pairs = find_bridge_pairs(filtered, top_n=5)
    if not pairs:
        log.warning(
            "No pairs found in goldilocks zone. "
            "Try widening SIMILARITY_LOW/HIGH in discoverer.py "
            "or extending LOOKBACK_HOURS in filter.py."
        )
        return

    if preview:
        print_preview(filtered, pairs)
        return

    # Step 4: synthesize 3 posts via LBD (+ inject preferences if any)
    digest = synthesize(pairs, preferences=preferences)

    # Step 5: publish to Telegram as 3 separate messages with 👍/👎 buttons
    try:
        success = publish(digest)
        if success:
            log.info("Digest published to Telegram.")
        else:
            log.warning("Telegram publish had errors — digest still saved locally.")
    except EnvironmentError as e:
        log.warning(f"Telegram skipped: {e}")

    # Step 6: save locally
    path = save_digest(digest)
    log.info(f"Digest saved: {path}")

    print("\n" + "=" * 60)
    print(digest)
    print("=" * 60)


if __name__ == "__main__":
    run(preview="--preview" in sys.argv)
