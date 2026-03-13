"""
telegram.py
Publishes the daily GTM feed as a single Telegram message.
Format: conversational header + numbered list of 5 articles,
each with a hyperlinked title, 1-2 line blurb, and Read more link.

Saves data/message_log.json so feedback.py can match emoji reactions.
"""

import json
import logging
import os
from datetime import datetime, timezone

import httpx

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
MAX_LENGTH = 4096
MESSAGE_LOG_PATH = "data/message_log.json"

HEADER = "Hey GTM Maxis! Here are your top GTM updates for today 👇"
OUTRO = "That's it for today. See you tomorrow. 👋"
SEPARATOR = "―――――――――――"


def _api(token: str, method: str, **kwargs) -> dict:
    url = TELEGRAM_API.format(token=token, method=method)
    try:
        resp = httpx.post(url, json=kwargs, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.error(f"Telegram API {method} failed: {e}")
        return {}


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_digest_message(posts: list[dict]) -> str:
    """Build a single HTML message with all posts as a numbered list."""
    lines = [HEADER, ""]

    for i, post in enumerate(posts, 1):
        headline = _escape_html(post.get("headline", post.get("title", "Untitled")))
        url = post.get("url", "")
        blurb = _escape_html(post.get("blurb", ""))

        lines.append(f"{i}. <b>{headline}</b>")
        lines.append("")
        if blurb:
            lines.append(blurb)
            lines.append("")
        lines.append(f'<a href="{url}">Read more →</a>')
        lines.append("")

    lines.append(OUTRO)
    return "\n".join(lines).strip()


def _save_message_log(message_id: int, posts: list[dict]):
    """Persist sent message metadata for feedback polling."""
    last_update_id = 0
    if os.path.exists(MESSAGE_LOG_PATH):
        try:
            with open(MESSAGE_LOG_PATH) as f:
                old = json.load(f)
            last_update_id = old.get("last_update_id", 0)
        except Exception:
            pass

    data = {
        "date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        "messages": [
            {
                "message_id": message_id,
                "post_index": 1,
                "snippet": HEADER,
                "urls": [p.get("url", "") for p in posts],
            }
        ],
        "last_update_id": last_update_id,
    }
    os.makedirs(os.path.dirname(MESSAGE_LOG_PATH), exist_ok=True)
    with open(MESSAGE_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    log.info("Message log saved.")


def publish(posts: list[dict]) -> bool:
    """
    Publish all enriched posts as a single Telegram message.
    Returns True if sent successfully.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel = os.environ.get("TELEGRAM_CHANNEL_ID")

    if not token or not channel:
        raise EnvironmentError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set in .env"
        )

    if not posts:
        log.warning("telegram: no posts to publish.")
        return False

    text = _build_digest_message(posts)
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH - 3] + "..."

    result = _api(
        token, "sendMessage",
        chat_id=channel,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    if result.get("ok"):
        message_id = result["result"]["message_id"]
        log.info(f"GTM feed published — message_id: {message_id}")
        _save_message_log(message_id, posts)
        return True
    else:
        log.error(f"Failed to publish feed: {result}")
        return False
