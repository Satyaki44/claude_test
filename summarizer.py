"""
summarizer.py
Synthesizes 3 Twitter posts via LBD bridge pairs + user preferences.
Each post is built on a bridge concept that neither source article explicitly states.
"""

import os
import logging
from groq import Groq

log = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """\
You write exactly like Satyaki — a tech founder, GTM strategist, and marketing analyst \
who runs a global agency. You write long-form posts on Twitter that get read in full \
because they have substance, flow, and real opinions.

Your writing style — follow strictly:
1. First-person, direct, no fluff
2. Short sentences. Vary the rhythm — some punchy, some longer.
3. Hook in the first line — make it impossible to scroll past
4. Develop the idea: introduce it, build context, share the insight, give your take
5. Use real data and specific examples from the source material
6. Casual but credible — like a sharp operator talking to smart peers
7. End with a strong personal opinion or a challenge to the reader
8. No em dashes. No jargon.
9. Target ~400 words per post. Enough depth to be genuinely useful.

FORMATTING — this is Twitter, not a blog:
- Add a blank line between every 2-3 sentences
- Numbered lists: each point on its own line, blank line between points
- No paragraph walls. Keep it scannable.
"""

SYNTHESIZE_PROMPT_TEMPLATE = """\
{preferences_block}\
Below are {n_pairs} pairs of articles from different GTM and AI marketing publications. \
Each pair was algorithmically matched because they are related but NOT identical — \
they share a conceptual neighbourhood without saying the same thing.

{pairs_block}

---

YOUR TASK — Literature-Based Discovery synthesis:

For each pair, there is a BRIDGE CONCEPT: an insight that connects Article A and \
Article B but that neither article explicitly states. Your job is to find that bridge \
and build a Twitter post around it.

The bridge is NOT a summary of either article. It is the idea that EMERGES from \
reading both together — a pattern, a contradiction, a consequence, or a reframe \
that neither author saw because they were writing about different things.

INSTRUCTIONS:

Step 1: Read all {n_pairs} pairs carefully.

Step 2: For each pair, identify the bridge concept in one sentence. \
What does reading A and B together reveal that neither A nor B says alone?

Step 3: Pick the 3 strongest bridges — the ones that produce the most genuine insight \
for a GTM practitioner or founder.

Step 4: Write one Twitter post per bridge. Each post must:
- Open with a hook that states or implies the bridge concept
- Reference what Article A says (specific, not vague)
- Reference what Article B says (specific, not vague)
- Arrive at the bridge insight as if you discovered it yourself
- End with your opinion or a challenge to the reader
- Feel like Satyaki wrote it from firsthand experience, not from reading newsletters
- NO attribution lines, no "Source:", no "Article A says"

Format your output exactly like this — nothing else:

---
POST 1

[Full post text — around 400 words]

---
POST 2

[Full post text — around 400 words]

---
POST 3

[Full post text — around 400 words]

---
"""


def _build_preferences_block(preferences: dict) -> str:
    liked = preferences.get("liked", [])
    disliked = preferences.get("disliked", [])
    if not liked and not disliked:
        return ""
    lines = ["PERSONALIZATION — based on your past feedback:\n"]
    if liked:
        lines.append("Posts you LIKED — lean into these angles:")
        for s in liked[-5:]:
            lines.append(f"  - {s[:150]}")
        lines.append("")
    if disliked:
        lines.append("Posts you DISLIKED — avoid these angles:")
        for s in disliked[-5:]:
            lines.append(f"  - {s[:150]}")
        lines.append("")
    lines.append("---\n\n")
    return "\n".join(lines)


def _format_pairs_block(pairs: list[dict]) -> str:
    sections = []
    for i, pair in enumerate(pairs, 1):
        a = pair["post_a"]
        b = pair["post_b"]
        sections.append(
            f"PAIR {i} (similarity: {pair['similarity']:.3f})\n"
            f"  Article A — [{a['publication']}] {a['title']}\n"
            f"  {a.get('summary', '')[:400]}\n"
            f"\n"
            f"  Article B — [{b['publication']}] {b['title']}\n"
            f"  {b.get('summary', '')[:400]}"
        )
    return "\n\n---\n\n".join(sections)


def synthesize(pairs: list[dict], preferences: dict = None) -> str:
    """
    Send bridge pairs to Groq. Returns 3 Twitter posts in Satyaki's voice.
    Injects user preferences (liked/disliked snippets) into the prompt if available.
    """
    if not pairs:
        return "No bridge pairs found — cannot synthesize digest."

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in .env")

    client = Groq(api_key=api_key)
    pairs_block = _format_pairs_block(pairs)
    preferences_block = _build_preferences_block(preferences or {})

    user_prompt = SYNTHESIZE_PROMPT_TEMPLATE.format(
        n_pairs=len(pairs),
        pairs_block=pairs_block,
        preferences_block=preferences_block,
    )

    log.info(f"Sending {len(pairs)} bridge pairs to {MODEL} for LBD synthesis")

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
