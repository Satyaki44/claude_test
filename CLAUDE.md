# GTM x AI Daily Digest — Project Bible

## What This Is
A daily digest pipeline that scrapes 20 GTM/AI publications, finds bridge insights between article pairs (LBD), synthesizes 3 Twitter posts in Satyaki's voice via Anthropic Claude Haiku, and publishes to Telegram. Runs on Render.com at 8 AM IST daily.

## Pipeline (in order)
1. `scraper.py` — RSS feeds via feedparser, 10s socket timeout
2. `filter.py` — Keeps last 7 days (168h), sorts newest first
3. `discoverer.py` — TF-IDF cosine similarity, goldilocks zone [0.15, 0.45], greedy dedup
4. `summarizer.py` — Claude Haiku LBD synthesis → 3 Twitter posts in Satyaki's voice
5. `telegram.py` — Publishes 3 posts as separate messages (no inline buttons)
6. `feedback.py` — Polls message_reaction events, saves to data/preferences.json
7. `main.py` — Orchestrates everything. `--preview` flag skips LLM + Telegram.

## How to Run
```bash
# Preview (no LLM, no Telegram — safe to run anytime)
python main.py --preview

# Full run (requires .env with all keys)
python main.py
```

## Key Files
- `main.py` — entry point
- `summarizer.py` — voice prompt, LBD synthesis logic
- `discoverer.py` — bridge pair algorithm
- `feedback.py` — reaction polling
- `data/preferences.json` — liked/disliked post snippets (grows over time)
- `data/message_log.json` — Telegram message IDs from last run
- `digests/` — saved markdown digests by date
- `tests/test_profiles.py` — Twitter/X profile scraper via Apify (standalone utility)

## Infrastructure
- **Scheduler**: Render.com cron, `02:30 UTC` = 8:00 AM IST
- **Branch**: `claude/initial-setup-JhDmH` → auto-deploys on push
- **Telegram channel**: `@dailygtmaicontent`

## Hard Rules — Never Break These
- Never fabricate statistics. If no real stat exists, skip it entirely.
- Never auto-commit or push without explicit user approval.
- Never display or share API keys in chat.
- Voice is Satyaki's: casual, "My 2 cents:" signature, abbreviations OK, no corporate tone.

## Environment Variables (see .env.example)
- `ANTHROPIC_API_KEY` — Claude Haiku synthesis
- `TELEGRAM_BOT_TOKEN` — publishing + reaction polling
- `TELEGRAM_CHANNEL_ID` — target channel
- `APIFY_API_KEY` — Twitter profile scraper (optional, tests only)
