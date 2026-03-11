"""
test_profiles.py
Scrapes the last 24 hours of tweets from specific Twitter/X profiles via Apify.
Runs all profiles in parallel for speed.

Usage:
    python3 tests/test_profiles.py
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROFILES = [
    "https://x.com/heynavtoor",
    "https://x.com/boringmarketer",
    "https://x.com/zeneca",
    "https://x.com/shannholmberg",
    "https://x.com/RoundtableSpace",
]

TWEETS_PER_PROFILE = 50
LOOKBACK_HOURS = 24
ACTOR_ID = "quacker/twitter-scraper"


def _url_to_handle(url: str) -> str:
    return url.strip().rstrip("/").split("?")[0].split("/")[-1]


def _parse_date(created_at: str):
    for fmt in ("%a %b %d %H:%M:%S +0000 %Y", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(created_at, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _within_window(created_at: str) -> bool:
    if not created_at:
        return True
    dt = _parse_date(created_at)
    if dt is None:
        return True  # can't parse → keep
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    return dt >= cutoff


def _normalize(item: dict, handle: str) -> dict:
    permalink = item.get("permalink", "")
    created_at = item.get("created_at", "")
    return {
        "text":     (item.get("full_text") or item.get("text") or "").strip(),
        "link":     f"https://x.com{permalink}" if permalink else "",
        "date":     created_at,
        "dt":       _parse_date(created_at),
        "likes":    item.get("favorite_count", 0),
        "retweets": item.get("retweet_count", 0),
        "replies":  item.get("reply_count", 0),
        "quotes":   item.get("quote_count", 0),
        "author":   item.get("user", {}).get("name", handle),
        "handle":   handle,
    }


def fetch_profile(api_key: str, profile_url: str) -> tuple[str, list[dict], list[dict]]:
    """Returns (handle, tweets_in_24h, all_tweets_sorted_by_date)."""
    handle = _url_to_handle(profile_url)
    client = ApifyClient(api_key)
    try:
        run = client.actor(ACTOR_ID).call(run_input={
            "startUrls": [{"url": profile_url}],
            "maxItems": TWEETS_PER_PROFILE,
        })
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        log.info(f"@{handle}: {len(items)} raw items fetched")
    except Exception as e:
        log.warning(f"@{handle}: failed — {e}")
        return handle, [], []

    all_normalized = [_normalize(item, handle) for item in items]
    # Sort by date descending (most recent first)
    all_normalized.sort(key=lambda x: x["dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    recent = [t for t in all_normalized if _within_window(t["date"])]
    recent.sort(key=lambda x: x["likes"], reverse=True)

    log.info(f"@{handle}: {len(recent)} tweets in last {LOOKBACK_HOURS}h")
    return handle, recent, all_normalized


def fetch_all_tweets() -> dict[str, list[dict]]:
    api_key = os.getenv("APIFY_API_KEY")
    if not api_key:
        raise RuntimeError("APIFY_API_KEY not set in .env")

    recent_map: dict[str, list[dict]] = {}
    all_map: dict[str, list[dict]] = {}

    # Run 2 at a time (free plan memory limit: 8192MB, each run uses 4096MB)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(fetch_profile, api_key, url): url for url in PROFILES}
        for future in as_completed(futures):
            handle, recent, all_tweets = future.result()
            recent_map[handle] = recent
            all_map[handle] = all_tweets

    order = [_url_to_handle(p) for p in PROFILES]
    return (
        {h: recent_map.get(h, []) for h in order},
        {h: all_map.get(h, []) for h in order},
    )


def _print_tweet(i: int, t: dict):
    eng = f"❤ {t['likes']}  🔁 {t['retweets']}  💬 {t['replies']}  🔖 {t['quotes']}"
    print(f"  #{i}  {eng}")
    print(f"       {t['date']}")
    for chunk in [t["text"][j:j+76] for j in range(0, max(len(t["text"]), 1), 76)]:
        print(f"       {chunk}")
    if t["link"]:
        print(f"       {t['link']}")
    print()


def print_results(recent_map: dict[str, list[dict]], all_map: dict[str, list[dict]]):
    total = sum(len(v) for v in recent_map.values())
    print(f"\n{'='*64}")
    print(f"  PROFILE FEED — last {LOOKBACK_HOURS}h  |  {total} tweets total")
    print(f"{'='*64}")

    for handle in recent_map:
        recent = recent_map[handle]
        all_tweets = all_map.get(handle, [])
        print(f"\n@{handle}  ({len(recent)} in last 24h)")
        print(f"  {'-'*54}")
        if recent:
            for i, t in enumerate(recent, 1):
                _print_tweet(i, t)
        elif all_tweets:
            print("  No tweets in last 24h — most recent 3:")
            print()
            for i, t in enumerate(all_tweets[:3], 1):
                _print_tweet(i, t)
        else:
            print("  (no data retrieved)")

    print(f"{'='*64}\n")


if __name__ == "__main__":
    import time
    t0 = time.time()
    recent_map, all_map = fetch_all_tweets()
    print_results(recent_map, all_map)
    log.info(f"Done in {time.time()-t0:.1f}s")
