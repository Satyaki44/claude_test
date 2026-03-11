# Skill: preview

Run the digest pipeline in preview mode — no LLM calls, no Telegram publishing.
Shows filtered posts and discovered bridge pairs only.

## Steps
1. Run `python main.py --preview` from the project root
2. Show the output to the user
3. Summarize: how many posts were fetched, how many bridge pairs found
4. If no pairs found, suggest widening SIMILARITY_LOW/HIGH in discoverer.py or extending LOOKBACK_HOURS in filter.py
