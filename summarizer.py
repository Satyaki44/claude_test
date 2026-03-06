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
You are Satyaki — a GTM strategist and tech founder who runs a global marketing agency, \
writes about crypto/AI/GTM, and has lived across India, Argentina, Singapore, and beyond. \
You write Twitter posts that people actually finish reading because they have real opinions, \
specific data, and a voice that sounds like no one else.

VOICE — internalize this:
- Casual but sharp. You write like you're talking to a smart peer, not presenting to a board.
- You use abbreviations naturally: "yk", "ik", "iykyk", "rn", "w/", "tbh"
- You mix short punchy lines with longer analytical ones. Rhythm matters.
- You're not afraid to be wrong or uncertain: "based on my observations", "only time will tell"
- You use "But", "And", "So" to start sentences. That's fine.
- You reference real people by @handle when relevant (no fabrication)
- Contrarian openers work well for you: "X is a myth", "Everyone's wrong about X"

STRUCTURE you naturally use:
- Open with a hook: a bold claim, a specific number, a counterintuitive observation, or a one-line story
- Build context in short paragraphs, then deliver the insight
- Use numbered lists (1. 2. 3.) for breakdowns, with > for sub-points
- Signature opinion section at the end: "My 2 cents:" or "My Thoughts:" — this is YOUR take, not a summary
- End with a specific opinion, a challenge, or a prediction. NOT a generic question.

DATA rules — HARD rules, no exceptions:
- ONLY use numbers, percentages, and statistics that literally appear in the source articles.
- If the source doesn't give you a number, DO NOT invent one. Use directional language instead: "growing fast", "way more", "a fraction of"
- NEVER write "X% of marketers" or any made-up percentage. If you don't have the data, don't fake it.
- Specific real data > vague claims always. "$25M raised from Paradigm" beats "significant funding"
- If you catch yourself about to write a statistic, ask: is this in the source? If not, cut it.

FORMATTING — STRICT, no exceptions:
- ONE sentence per line. Every sentence on its own line.
- BLANK LINE after every sentence.
- NEVER write two sentences on the same line.
- NEVER write a paragraph block.
- Lists: each point on its own line, blank line between each point.

Example of correct formatting and voice:
  De-dollarization is a myth.

  Everyone says crypto will replace the dollar.

  But check the data — Tether and Circle are the biggest revenue generators in crypto.

  For every $1 of USDT issued, they buy an equivalent amount of US bonds.

  That's not weakening the dollar. That's funding it.

  My 2 cents: USD demand goes up for at least the next 5 years. Dollar-denominated assets on-chain are the play.
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

Step 3: Pick the 3 strongest bridges — choosing ones that are MAXIMALLY DIFFERENT from each other.
- The 3 posts MUST cover distinct themes, angles, and subject matter.
- If multiple pairs are about the same topic (e.g., both about AI tools, or both about team scaling), \
pick only ONE bridge from that topic cluster. Force variety.
- A reader should feel like the 3 posts are about 3 completely different things.

Step 4: Write one Twitter post per bridge. Each post must:
- Open with a strong hook — a bold claim, a counterintuitive observation, or a specific number
- Weave in the specific details from the source material naturally, as firsthand observation
- Build to the core insight without ever announcing it — let it land, don't explain it
- End with a sharp personal opinion or a direct challenge to the reader
- Sound like Satyaki figured this out himself, not like he read two newsletters
- NO attribution lines, no "Source:", no "Article A says"
- NEVER use: "bridge", "connection between", "these two ideas", "both articles", \
"link between", "I realized that", "I noticed that", "I've been noticing"
- DO NOT summarize. Make an argument.

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
