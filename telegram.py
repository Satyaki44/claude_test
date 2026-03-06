"""
telegram.py
Publishes 3 digest posts as separate Telegram messages, each with 👍/👎 buttons.
Saves message_log.json so feedback.py can match reactions tomorrow.

Setup (one-time):
  1. Message @BotFather on Telegram → /newbot → copy the token
  2. Add your bot to your channel as admin
  3. Add to .env:
       TELEGRAM_BOT_TOKEN=your_token_here
       TELEGRAM_CHANNEL_ID=@yourchannel   (or numeric: -100xxxxxxxxxx)
"""

import json
import logging
import os
import re
from datetime import datetime, timezone

import httpx

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
MAX_LENGTH = 4096
MESSAGE_LOG_PATH = "message_log.json"


def _api(token: str, method: str, **kwargs) -> dict:
    url = TELEGRAM_API.format(token=token, method=method)
    try:
        resp = httpx.post(url, json=kwargs, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.error(f"Telegram API {method} failed: {e}")
        return {}


def _parse_posts(digest: str) -> list[str]:
    """Split digest string into individual posts using the ---\\nPOST N delimiter."""
    parts = re.split(r"-{3,}\s*\nPOST \d+\s*\n", digest)
    posts = []
    for part in parts:
        cleaned = part.strip().rstrip("-").strip()
        if len(cleaned) > 20:   # ignore tiny fragments
            posts.append(cleaned)
    return posts


def _save_message_log(messages: list[dict]):
    """Persist sent message metadata for tomorrow's feedback poll."""
    # Preserve last_update_id across runs
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
        "messages": messages,
        "last_update_id": last_update_id,
    }
    with open(MESSAGE_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Message log saved: {len(messages)} entries")


def publish(digest: str) -> bool:
    """
    Parse digest into individual posts and send each as a separate Telegram message
    with 👍/👎 inline keyboard buttons.
    Returns True if all messages sent successfully.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel = os.environ.get("TELEGRAM_CHANNEL_ID")

    if not token or not channel:
        raise EnvironmentError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set in .env"
        )

    posts = _parse_posts(digest)

    if not posts:
        log.warning("Could not parse posts from digest — sending as single message.")
        result = _api(token, "sendMessage", chat_id=channel, text=digest[:MAX_LENGTH])
        return result.get("ok", False)

    log.info(f"Sending {len(posts)} posts as separate Telegram messages")
    sent_messages = []
    all_ok = True

    for i, post_text in enumerate(posts, 1):
        if len(post_text) > MAX_LENGTH:
            post_text = post_text[:MAX_LENGTH - 3] + "..."

        keyboard = {
            "inline_keyboard": [[
                {"text": "👍", "callback_data": f"like_{i}"},
                {"text": "👎", "callback_data": f"dislike_{i}"},
            ]]
        }

        result = _api(
            token, "sendMessage",
            chat_id=channel,
            text=post_text,
            reply_markup=keyboard,
        )

        if result.get("ok"):
            message_id = result["result"]["message_id"]
            sent_messages.append({
                "message_id": message_id,
                "post_index": i,
                "snippet": post_text[:200],
            })
            log.info(f"Sent post {i}/{len(posts)} — message_id: {message_id}")
        else:
            log.error(f"Failed to send post {i}: {result}")
            all_ok = False

    _save_message_log(sent_messages)
    return all_ok
