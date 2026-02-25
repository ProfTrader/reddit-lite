---
name: reddit-lite
description: Read and monitor Reddit without official API keys using subreddit feeds, search, thread JSON, comments, and social metrics. Use when users need Bird-CLI-style latest Reddit data pulls, read-only analytics, and cron-ready monitoring.
---

# Reddit Lite Skill (Read-Only)

Use this skill for Reddit ingestion and monitoring only (no posting/commenting/voting).

## Run the Script

Script path:

`/root/.openclaw/workspace/skills/reddit-lite/scripts/reddit_lite.py`

Common commands:

```bash
# Latest posts from a subreddit
python3 reddit_lite.py subreddit --name LocalLLaMA --sort new --limit 25

# Search Reddit (all or single subreddit)
python3 reddit_lite.py search --query "prop trading" --sort new --limit 25
python3 reddit_lite.py search --query "prop trading" --subreddit wallstreetbets --sort new --limit 25

# Full thread + nested comments + metrics
python3 reddit_lite.py thread --url "https://www.reddit.com/r/python/comments/abc123/example/"

# Monitor (dedupe + SQLite), cron-friendly
python3 reddit_lite.py monitor --subreddit LocalLLaMA --sort new --limit 50
python3 reddit_lite.py monitor --query "prediction markets" --sort new --limit 50

# Rank top opportunities from stored data
python3 reddit_lite.py summary --window 500 --top 10
python3 reddit_lite.py summary --query "prop trading" --window 1000 --top 15
```

## Metrics Available

- `score`
- `ups` (when present)
- `upvote_ratio`
- `estimated_downs` (derived estimate when possible)
- `num_comments`
- `total_awards_received`
- `num_crossposts`
- `created_utc`
- `permalink`

## Important Data Reality

Reddit does not reliably expose exact downvote counts on all content. Use `estimated_downs` where needed.

## References

Read cron patterns and mode notes in:

- `/root/.openclaw/workspace/skills/reddit-lite/references/modes.md`
