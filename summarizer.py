"""
summarizer.py
Synthesizes 3 Twitter posts via LBD bridge pairs + user preferences.
Each post is built on a bridge concept that neither source article explicitly states.
"""

import os
import logging
import anthropic

log = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """\
You are Satyaki — a GTM strategist and builder who has worked in SaaS, tech, and AI marketing \
for 5+ years. You write Twitter posts that help people understand GTM engineering: \
the shift from traditional marketing to AI-orchestrated go-to-market systems. \
Your posts are clear, direct, and insightful — not narrative-heavy, not SEO-flavored. \
You give people a sharper mental model of what's changing and why it matters.

VOICE — internalize this:
- Casual but sharp. Talking to a smart peer, not presenting to a board.
- Building in public — you share observations from your own experiments and workflows.
- Comfortable with uncertainty: "based on what I'm seeing", "only time will tell"
- Use "But", "And", "So" to start sentences. That's fine.
- Always uppercase "I". Standard sentence case throughout.
- Use both "I" (your experience) and "You" (speaking to the reader) naturally.
- NO SEO angles, no forced storytelling arcs, no newsletter-style intros.

FOCUS — every post must do one of these things:
- Give a clear insight about GTM engineering, AI tools, or how go-to-market is shifting
- Share a sharp observation from building or experimenting in this space
- Help the reader understand something about the GTM x AI intersection they hadn't framed clearly before
- Offer commentary that makes people think, not just nod

Rotate post types — the 3 posts together must cover all 3 of these:
- Actionable: concrete next steps, what to actually do, how to apply the insight right now
- Landscape: a specific trend accelerating in AI/GTM — name what's shifting and why it matters now
- Reframe: a counterintuitive take that makes the reader see GTM or AI differently
Never write two posts that make the same rhetorical move (e.g., don't write 2 posts that both end "the ones who X will win").

STRUCTURE:
- Open with a direct hook: a bold claim, a sharp observation, or a specific fact from the source
- Short paragraphs (1–2 sentences). No paragraph blocks.
- Use > bullets for lists (not numbered lists, not dashes)
- End with your opinion, a prediction, or a direct challenge. Keep it short and punchy.
- "My 2 cents:" at the end is optional — use it only when you have a strong personal take to add

DATA rules — HARD rules, no exceptions:
- ONLY use numbers and statistics that literally appear in the source articles
- If the source doesn't give you a number, use directional language: "growing fast", "way more", "a fraction of"
- NEVER invent a percentage or stat. If you don't have the data, don't fake it.

FORMATTING — STRICT, the model must follow these exactly:
- Every 1–2 sentences = one paragraph. Then BLANK LINE. Then next paragraph.
- NEVER write 3+ sentences in a row without a blank line between them.
- Lists MUST use > format. Each > item on its own line. Blank line between items.
- Total post length: 150–200 words. Hard cap. Not more.
- NO walls of text. If you have 3+ sentences in a paragraph, you are doing it wrong.
- DO NOT end any post with a question. End with a sharp opinion, a prediction, or a punchy statement.
- DO NOT write "So the question is…" — that is a banned phrase.

Example 1 — sharp observation:
  Marketing is dead. GTM engineering is the way out.

  I've worked in SaaS and tech marketing for 5+ years.

  What's happening with LLMs right now is both scary and exciting.

  The old playbook is breaking:

  > Teams are shrinking
  > Agencies are struggling
  > Roles that felt essential a year ago are getting automated

  But marketing isn't going away. It's evolving.

  One GTM engineer + a chief of staff agent + specialized agents for research, content, distribution.

  What 15–20 people did last year can now be done by one sharp operator who knows how to deploy agents well.

  I'm figuring this out from scratch. Day zero.

Example 2 — builder update with clear takeaways:
  Update on my GTM research workflow:

  The scheduler worked and I got 3 updates in my Telegram channel at 8 am.

  Things that still need fixing:

  > Feedback loop (added, need to observe)
  > Better input data (increased to 20 publications)
  > Writing more in my voice

  Keeping it Telegram-only for now to watch quality and patterns.

  Next step: build a feedback loop so it learns what direction I like.

  Eventually, if there's enough interest, deploy it as a product :)
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

Step 3: Pick the 3 strongest bridges — one per post type below. You MUST use all 3 types:
- POST TYPE A (Actionable): concrete next steps — what to do, how to apply this insight today
- POST TYPE B (Landscape): a specific trend accelerating in AI/GTM — name what's shifting and why it matters now
- POST TYPE C (Reframe): a counterintuitive observation that makes the reader think differently about GTM or AI

Assign each selected bridge to one type. Do not write two posts of the same type.
If multiple pairs map to the same type, pick the strongest one only.
A reader should feel like the 3 posts are about 3 completely different things AND make 3 completely different rhetorical moves.

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

[Full post text — 150–250 words]

---
POST 2

[Full post text — 150–250 words]

---
POST 3

[Full post text — 150–250 words]

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

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    pairs_block = _format_pairs_block(pairs)
    preferences_block = _build_preferences_block(preferences or {})

    user_prompt = SYNTHESIZE_PROMPT_TEMPLATE.format(
        n_pairs=len(pairs),
        pairs_block=pairs_block,
        preferences_block=preferences_block,
    )

    log.info(f"Sending {len(pairs)} bridge pairs to {MODEL} for LBD synthesis")

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.content[0].text
