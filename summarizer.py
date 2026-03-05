"""
summarizer.py
Reads filtered Substack posts and generates 3 standalone Twitter posts
in Satyaki's voice, focused on GTM x AI themes.
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

USER_PROMPT_TEMPLATE = """\
Below are recent posts from 10 top GTM, AI, and marketing newsletters. \
Read ALL of them carefully before writing anything.

{post_block}

---

IMPORTANT INSTRUCTIONS:

Step 1: Read everything above. Identify the strongest signals, patterns, data points, \
and contrarian ideas across ALL sources. Think about what connects them. \
What are the 3 most interesting angles you can write about?

Step 2: For each post, you may:
- Synthesize insights from multiple publications into one cohesive argument
- Use one strong publication as the anchor but weave in related ideas from others
- In rare cases, if one piece has an exceptionally strong standalone insight, write a \
  deep dive on just that — but still bring your own analysis and perspective

Step 3: Write 3 separate, standalone long-form Twitter posts.

Themes to explore (not all required, pick the strongest angles from the material):
- How AI is fundamentally changing GTM and marketing operations
- Is content marketing dead, or is it evolving into something else?
- The shift from growth hackers to GTM engineers — what changed and why
- AI tools that are producing real, measurable results for revenue teams
- What founders and CMOs are actually saying vs. what is hype
- Any other strong signal you found across the 10 publications

Each post must:
- Start with a strong hook on its own line
- Flow: hook → context → insight → your take → strong ending
- Blank line between every 2-3 sentences — scannable, not dense
- Feel like Satyaki wrote it from his own experience, not a newsletter recap
- NO source line or attribution at the end

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


def _format_post_block(posts: list[dict]) -> str:
    lines = []
    for i, p in enumerate(posts[:30], 1):
        lines.append(
            f"{i}. [{p['publication']}] {p['title']}\n"
            f"   Date: {p['date']}\n"
            f"   {p['summary']}\n"
            f"   {p['url']}\n"
        )
    return "\n".join(lines)


def summarize(posts: list[dict]) -> str:
    """
    Call Groq (Llama 3.3 70B) with filtered posts.
    Returns 3 Twitter posts in Satyaki's voice.
    Requires GROQ_API_KEY in environment.
    """
    if not posts:
        return "No posts found in the last 7 days across all sources."

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in .env")

    client = Groq(api_key=api_key)
    post_block = _format_post_block(posts)
    user_prompt = USER_PROMPT_TEMPLATE.format(post_block=post_block)

    log.info(f"Sending {min(len(posts), 30)} posts to {MODEL} for Twitter post generation")

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
