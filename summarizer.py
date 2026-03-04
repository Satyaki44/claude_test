"""
summarizer.py
Sends filtered tweets to Claude and gets back a structured daily digest.
"""

import os
import logging
import anthropic

log = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"   # fast + cheap for daily digest

SYSTEM_PROMPT = """\
You are an expert analyst covering the intersection of Go-To-Market (GTM) strategy \
and software engineering. Your job is to read a set of high-engagement tweets and \
produce a concise, insightful daily digest for a technical founder or engineering leader.
"""

USER_PROMPT_TEMPLATE = """\
Below are today's high-signal tweets about GTM engineering, developer-led growth, \
RevOps, sales engineering, and related topics. Each tweet includes author, likes, \
retweets, and text.

{tweet_block}

---

Please produce a digest with the following sections:

## Key Themes Today
3-5 bullet points summarising the dominant topics and conversations.

## Top Tweets Worth Reading
List the 5 most insightful tweets. For each, include:
- Author (@handle)
- Why it matters (1-2 sentences)
- Direct link

## Actionable Takeaways
2-3 concrete things a technical GTM or engineering leader could act on this week, \
drawn from the tweets.

Keep the tone direct and practitioner-focused. No fluff.
"""


def _format_tweet_block(tweets: list[dict]) -> str:
    lines = []
    for i, t in enumerate(tweets[:30], 1):   # cap at 30 to stay within context
        lines.append(
            f"{i}. @{t['handle']} ({t['likes']} likes, {t['retweets']} RT)\n"
            f"   {t['text']}\n"
            f"   {t['link']}\n"
        )
    return "\n".join(lines)


def summarize(tweets: list[dict]) -> str:
    """
    Call Claude with the filtered tweets and return the digest as a string.
    Requires ANTHROPIC_API_KEY in environment.
    """
    if not tweets:
        return "No high-signal tweets found today."

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    tweet_block = _format_tweet_block(tweets)
    user_prompt = USER_PROMPT_TEMPLATE.format(tweet_block=tweet_block)

    log.info(f"Sending {min(len(tweets), 30)} tweets to {MODEL} for summarisation")

    message = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text
