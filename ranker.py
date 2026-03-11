"""
ranker.py
Scores and ranks articles by GTM relevance + recency.
Returns top N articles with source diversity enforcement.

Replaces discoverer.py — no bridge pairs, just quality-based selection.
"""

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

log = logging.getLogger(__name__)

TOP_N = 5
MAX_PER_SOURCE = 2

# GTM-specific keywords — Tier 1 is high-signal (weight 2), Tier 2 is context (weight 1)
TIER1_KEYWORDS = [
    "outbound", "pipeline", "revenue", "gtm engineer", "sales motion", "icp",
    "go-to-market", "gtm", "sales", "prospect", "lead generation", "conversion",
    "churn", "retention", "expansion", "customer success", "account executive",
    "sdr", "bdr", "cold email", "sequencing", "playbook", "quota", "deal",
    "funnel", "mrr", "arr", "win rate", "close rate",
]

TIER2_KEYWORDS = [
    "ai agent", "automation", "claude", "llm", "workflow", "crm", "salesforce",
    "hubspot", "apollo", "clay", "outreach", "artificial intelligence",
    "generative ai", "copilot", "gpt", "productivity", "tool", "stack",
    "operator", "builder", "engineer", "strategy",
]


def _keyword_score(post: dict) -> float:
    text = f"{post.get('title', '')} {post.get('summary', '')}".lower()
    score = 0.0
    for kw in TIER1_KEYWORDS:
        if kw in text:
            score += 2.0
    for kw in TIER2_KEYWORDS:
        if kw in text:
            score += 1.0
    return score


def _recency_score(post: dict) -> float:
    """Returns 0.0–1.0 based on recency within the 24h window. Newest = 1.0."""
    date_str = post.get("date", "")
    if not date_str:
        return 0.5
    try:
        dt = parsedate_to_datetime(date_str)
    except Exception:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return 0.5
    now = datetime.now(tz=timezone.utc)
    age_hours = (now - dt).total_seconds() / 3600
    return max(0.0, 1.0 - (age_hours / 24.0))


def rank_posts(posts: list[dict], top_n: int = TOP_N) -> list[dict]:
    """
    Score all posts by GTM relevance + recency.
    Enforce source diversity (max MAX_PER_SOURCE per publication).
    Return top_n posts sorted by score.
    """
    if not posts:
        log.warning("ranker: no posts to rank.")
        return []

    scored = []
    for post in posts:
        kw = _keyword_score(post)
        rec = _recency_score(post)
        # Keyword relevance is primary; recency breaks ties
        total = kw + (rec * 0.5)
        scored.append((total, post))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Apply source diversity cap
    source_counts: dict[str, int] = {}
    selected = []
    for score, post in scored:
        pub = post.get("publication", "unknown")
        if source_counts.get(pub, 0) < MAX_PER_SOURCE:
            selected.append(post)
            source_counts[pub] = source_counts.get(pub, 0) + 1
        if len(selected) == top_n:
            break

    log.info(f"ranker: {len(posts)} posts → top {len(selected)} selected")
    for p in selected:
        log.info(f"  [{p.get('publication', '?')}] {p.get('title', '')[:70]}")

    return selected
