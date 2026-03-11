"""
summarizer.py
For each top-ranked article, generates a 2-3 sentence summary and
a 1-sentence GTM angle using Claude Sonnet.

Returns enriched post dicts with 'summary_text' and 'gtm_angle' fields added.
"""

import json
import logging
import os

import anthropic

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You curate a daily GTM intelligence feed for salespeople, revenue operators, marketers, \
and GTM engineers. Your readers are practitioners — they want to know what's happening \
and what it means for their pipeline, their stack, their team, or their workflow. \
They don't need fluff. They need clarity.

Rules:
- ONLY use information explicitly present in the article title and description. Never invent.
- Write like you're briefing a sharp GTM colleague, not summarizing for a report.
- The headline must be short — 6 to 8 words max. Rewrite to say exactly what the article \
is about, in plain language. No colons, no em-dashes, no clickbait. Just the point.
- The blurb is 2 sentences max. Sentence 1: the key finding or argument in the article. \
Sentence 2: the direct implication for GTM — specific to pipeline, stack, hiring, or workflow. \
No generic takeaways.
- No filler phrases like "this is important", "in today's landscape", "as AI continues to".
"""

PROMPT_TEMPLATE = """\
Process the following {n} articles for a daily GTM intelligence feed.

For each article return valid JSON only, no preamble:

{{
  "articles": [
    {{
      "index": 1,
      "headline": "Rewritten headline — specific and punchy. Use original if already sharp.",
      "blurb": "Sentence 1: key insight from the article. Sentence 2: what it means for GTM practitioners specifically."
    }}
  ]
}}

Articles:

{articles_block}
"""


def _format_articles_block(posts: list[dict]) -> str:
    blocks = []
    for i, post in enumerate(posts, 1):
        blocks.append(
            f"ARTICLE {i}\n"
            f"Title: {post.get('title', 'No title')}\n"
            f"Publication: {post.get('publication', 'Unknown')}\n"
            f"Author: {post.get('author', 'Unknown')}\n"
            f"Description: {post.get('summary', 'No description available')[:600]}"
        )
    return "\n\n---\n\n".join(blocks)


def synthesize(posts: list[dict], preferences: dict = None) -> list[dict]:
    """
    Takes top-ranked posts. Returns list of post dicts enriched with
    'summary_text' and 'gtm_angle' fields.
    """
    if not posts:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    articles_block = _format_articles_block(posts)

    user_prompt = PROMPT_TEMPLATE.format(
        n=len(posts),
        articles_block=articles_block,
    )

    log.info(f"Sending {len(posts)} articles to {MODEL} for summarization")

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if model wraps output
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
        summaries = data.get("articles", [])
    except json.JSONDecodeError as e:
        log.error(f"summarizer: JSON parse failed — {e}\nRaw output: {raw[:300]}")
        return [dict(p, blurb="") for p in posts]

    # Merge blurbs back into post dicts
    result = []
    for i, post in enumerate(posts, 1):
        match = next((s for s in summaries if s.get("index") == i), None)
        enriched = dict(post)
        enriched["headline"] = match.get("headline", post.get("title", "")) if match else post.get("title", "")
        enriched["blurb"] = match.get("blurb", "") if match else ""
        result.append(enriched)

    return result
