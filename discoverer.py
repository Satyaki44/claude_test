"""
discoverer.py
Literature-Based Discovery via TF-IDF cosine similarity.

Finds article pairs in the "goldilocks zone": related but not identical,
from different publications — the sweet spot for novel synthesis.
"""

import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)

# Goldilocks zone calibrated for TF-IDF (not dense embeddings).
# TF-IDF cosine similarities are lower than sentence-transformers by design.
SIMILARITY_LOW  = 0.15   # below: too unrelated to bridge meaningfully
SIMILARITY_HIGH = 0.45   # above: too redundant, same idea rephrased


def find_bridge_pairs(posts: list[dict], top_n: int = 5) -> list[dict]:
    """
    Given filtered posts, return up to top_n pairs in the goldilocks zone
    from different publications.

    Each returned dict: {post_a, post_b, similarity}
    """
    if len(posts) < 2:
        log.warning("discoverer: fewer than 2 posts — cannot find pairs.")
        return []

    # Title doubled to boost its TF-IDF weight vs. long summaries
    texts = [
        f"{p['title']} {p['title']} {p.get('summary', '')}"
        for p in posts
    ]

    vectorizer = TfidfVectorizer(min_df=1, stop_words="english", max_features=5000)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError as e:
        log.error(f"discoverer: TF-IDF failed — {e}")
        return []

    sim_matrix = cosine_similarity(tfidf_matrix)

    pairs = []
    n = len(posts)
    for i in range(n):
        for j in range(i + 1, n):
            score = float(sim_matrix[i, j])
            if (SIMILARITY_LOW <= score <= SIMILARITY_HIGH
                    and posts[i]["publication"] != posts[j]["publication"]):
                pairs.append({
                    "post_a":     posts[i],
                    "post_b":     posts[j],
                    "similarity": round(score, 4),
                })

    if not pairs:
        log.warning(
            f"discoverer: no pairs in goldilocks zone "
            f"[{SIMILARITY_LOW}, {SIMILARITY_HIGH}] across different publications."
        )
        return []

    pairs.sort(key=lambda x: x["similarity"], reverse=True)
    selected = pairs[:top_n]

    log.info(f"discoverer: {len(pairs)} candidate pairs → returning top {len(selected)}")
    for p in selected:
        log.info(
            f"  [{p['similarity']:.3f}] "
            f"{p['post_a']['publication']} × {p['post_b']['publication']}: "
            f"\"{p['post_a']['title'][:40]}\" ↔ \"{p['post_b']['title'][:40]}\""
        )

    return selected
