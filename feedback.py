"""
feedback.py
Polls Telegram for 👍/👎 callback_query feedback from previous digest messages.
Updates preferences.json so tomorrow's digest learns from today's reactions.

Flow:
  - Cron sends 3 messages with inline buttons, saves message_log.json
  - Next day's cron calls poll_and_process_feedback() first
  - Any button presses since last run are retrieved and recorded
  - preferences.json grows over time, injected into Groq prompt
"""

import json
import logging
import os
import httpx

log = logging.getLogger(__name__)

MESSAGE_LOG_PATH = "message_log.json"
PREFERENCES_PATH = "preferences.json"
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def load_message_log() -> dict:
    if os.path.exists(MESSAGE_LOG_PATH):
        with open(MESSAGE_LOG_PATH) as f:
            return json.load(f)
    return {}


def save_message_log(data: dict):
    with open(MESSAGE_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_preferences() -> dict:
    if os.path.exists(PREFERENCES_PATH):
        with open(PREFERENCES_PATH) as f:
            return json.load(f)
    return {"liked": [], "disliked": []}


def save_preferences(prefs: dict):
    with open(PREFERENCES_PATH, "w") as f:
        json.dump(prefs, f, indent=2)


def _api(token: str, method: str, **kwargs) -> dict:
    url = TELEGRAM_API.format(token=token, method=method)
    try:
        resp = httpx.post(url, json=kwargs, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning(f"Telegram API {method} failed: {e}")
        return {}


def poll_and_process_feedback(token: str) -> dict:
    """
    Poll Telegram getUpdates for callback_queries from previous messages.
    Matches them against message_log.json, updates preferences.json.
    Returns updated preferences dict.
    """
    msg_log = load_message_log()
    prefs = load_preferences()

    if not msg_log or not msg_log.get("messages"):
        log.info("feedback: no message log found — skipping feedback poll.")
        return prefs

    # Build lookup: message_id → post snippet
    msg_lookup = {
        entry["message_id"]: entry["snippet"]
        for entry in msg_log.get("messages", [])
    }

    last_update_id = msg_log.get("last_update_id", 0)
    params = {
        "allowed_updates": ["callback_query"],
        "timeout": 5,
        "limit": 100,
    }
    if last_update_id:
        params["offset"] = last_update_id + 1

    result = _api(token, "getUpdates", **params)
    updates = result.get("result", [])

    if not updates:
        log.info("feedback: no new callback updates.")
        return prefs

    new_last_id = last_update_id
    feedback_count = 0

    for update in updates:
        update_id = update.get("update_id", 0)
        new_last_id = max(new_last_id, update_id)

        cq = update.get("callback_query")
        if not cq:
            continue

        data = cq.get("data", "")          # "like_1" or "dislike_2"
        msg_id = cq.get("message", {}).get("message_id")
        callback_id = cq.get("id")

        # Acknowledge immediately (clears loading state for the user)
        _api(token, "answerCallbackQuery",
             callback_query_id=callback_id,
             text="Got it! Thanks for the feedback.")

        snippet = msg_lookup.get(msg_id)
        if not snippet:
            log.warning(f"feedback: no snippet for message_id {msg_id}")
            continue

        if data.startswith("like_"):
            if snippet not in prefs["liked"]:
                prefs["liked"].append(snippet)
            # Remove from disliked if it was there
            prefs["disliked"] = [d for d in prefs["disliked"] if d != snippet]
            log.info(f"feedback: 👍 recorded — message {msg_id}")
            feedback_count += 1

        elif data.startswith("dislike_"):
            if snippet not in prefs["disliked"]:
                prefs["disliked"].append(snippet)
            prefs["liked"] = [l for l in prefs["liked"] if l != snippet]
            log.info(f"feedback: 👎 recorded — message {msg_id}")
            feedback_count += 1

    # Keep preferences lists bounded (last 30 entries each)
    prefs["liked"] = prefs["liked"][-30:]
    prefs["disliked"] = prefs["disliked"][-30:]

    # Save updated offset so next run doesn't reprocess
    msg_log["last_update_id"] = new_last_id
    save_message_log(msg_log)

    if feedback_count:
        save_preferences(prefs)
        log.info(
            f"feedback: {feedback_count} reactions processed — "
            f"{len(prefs['liked'])} liked, {len(prefs['disliked'])} disliked total"
        )
    else:
        log.info("feedback: updates found but no relevant button presses.")

    return prefs
