"""
main.py
GTM Feed — daily curation pipeline.

Run locally:       python3 main.py
Preview (no LLM):  python3 main.py --preview
Run via cron:      render.yaml (12:30 UTC = 6:00 PM IST)
"""

import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from scraper import fetch_posts
from filter import filter_posts
from ranker import rank_posts
from summarizer import synthesize
from telegram import publish

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

DIGESTS_DIR = "digests"


def save_digest(posts: list[dict]) -> str:
    os.makedirs(DIGESTS_DIR, exist_ok=True)
    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(DIGESTS_DIR, f"{date_str}.md")
    with open(path, "w") as f:
        f.write(f"# GTM Feed — {date_str}\n\n")
        for i, post in enumerate(posts, 1):
            f.write(f"## {i}. {post.get('title', 'Untitled')}\n")
            f.write(f"**{post.get('publication', '')}** · {post.get('url', '')}\n\n")
            if post.get("blurb"):
                f.write(f"{post['blurb']}\n\n")
            f.write("---\n\n")
    return path


def print_preview(posts: list[dict]):
    print(f"\n{'='*60}")
    print(f"  GTM FEED PREVIEW — {len(posts)} articles ranked")
    print(f"{'='*60}\n")
    for i, p in enumerate(posts, 1):
        print(f"#{i}  [{p.get('publication', '?')}]")
        print(f"    {p.get('title', 'No title')}")
        print(f"    {p.get('url', '')}")
        print()


def run(preview: bool = False):
    log.info("=== GTM Feed ===")

    # Step 1: scrape all RSS sources
    raw_posts = fetch_posts()
    if not raw_posts:
        log.warning("No posts fetched. Check feed URLs or network.")
        return

    # Step 2: filter to last 24h
    filtered = filter_posts(raw_posts)
    if not filtered:
        log.warning("No posts from the last 24h. Feed may be quiet today.")
        return

    # Step 3: rank by GTM relevance + recency, pick top 5
    ranked = rank_posts(filtered)
    if not ranked:
        log.warning("No posts passed ranking. Try adjusting keyword weights in ranker.py.")
        return

    if preview:
        print_preview(ranked)
        return

    # Step 4: summarize — add summary_text + gtm_angle to each post
    enriched = synthesize(ranked)

    # Step 5: publish to Telegram
    try:
        success = publish(enriched)
        if success:
            log.info("Feed published to Telegram.")
        else:
            log.warning("Some Telegram messages failed — digest still saved locally.")
    except EnvironmentError as e:
        log.warning(f"Telegram skipped: {e}")
        enriched = enriched or ranked

    # Step 6: save locally
    path = save_digest(enriched or ranked)
    log.info(f"Digest saved: {path}")


if __name__ == "__main__":
    run(preview="--preview" in sys.argv)
