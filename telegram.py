"""
telegram.py
Publishes the digest to a Telegram channel via Bot API.

Setup (one-time):
  1. Message @BotFather on Telegram → /newbot → copy the token
  2. Add your bot to your channel as admin
  3. Add to .env:
       TELEGRAM_BOT_TOKEN=your_token_here
       TELEGRAM_CHANNEL_ID=@yourchannel   (or numeric: -100xxxxxxxxxx)
"""

import os
import logging
import httpx

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LENGTH = 4096  # Telegram message character limit


def publish(text: str) -> bool:
    """
    Send text to the configured Telegram channel.
    Splits into multiple messages if text exceeds Telegram's 4096 char limit.
    Returns True on success, False on failure.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel = os.environ.get("TELEGRAM_CHANNEL_ID")

    if not token or not channel:
        raise EnvironmentError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set in .env"
        )

    url = TELEGRAM_API.format(token=token)
    chunks = _split_message(text)

    for i, chunk in enumerate(chunks):
        try:
            resp = httpx.post(
                url,
                json={"chat_id": channel, "text": chunk, "parse_mode": "Markdown"},
                timeout=10,
            )
            resp.raise_for_status()
            log.info(f"Telegram: sent chunk {i+1}/{len(chunks)}")
        except Exception as e:
            log.error(f"Telegram publish failed: {e}")
            return False

    return True


def _split_message(text: str) -> list[str]:
    """Split text into chunks that fit within Telegram's 4096 char limit."""
    if len(text) <= MAX_LENGTH:
        return [text]

    chunks = []
    while text:
        if len(text) <= MAX_LENGTH:
            chunks.append(text)
            break
        # Split at last newline before the limit
        split_at = text.rfind("\n", 0, MAX_LENGTH)
        if split_at == -1:
            split_at = MAX_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks
