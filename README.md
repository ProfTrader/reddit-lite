# reddit-lite

Read-only Reddit ingestion skill for OpenClaw.

## Features
- Latest subreddit pulls (`new/hot/top/rising`)
- Reddit search (global or subreddit-scoped)
- Full thread + nested comments via `/.json`
- Social metrics: `score`, `ups`, `upvote_ratio`, `estimated_downs`, `num_comments`, awards, crossposts
- Monitor mode with SQLite dedupe (cron-ready)
- Summary mode to rank opportunities by engagement + recency

## Install/Use (local)
```bash
python3 /root/.openclaw/workspace/skills/reddit-lite/scripts/reddit_lite.py subreddit --name LocalLLaMA --sort new --limit 25
python3 /root/.openclaw/workspace/skills/reddit-lite/scripts/reddit_lite.py search --query "prop trading" --sort new --limit 25
python3 /root/.openclaw/workspace/skills/reddit-lite/scripts/reddit_lite.py thread --url "https://www.reddit.com/r/.../comments/.../"
python3 /root/.openclaw/workspace/skills/reddit-lite/scripts/reddit_lite.py monitor --query "prediction markets" --sort new --limit 50
python3 /root/.openclaw/workspace/skills/reddit-lite/scripts/reddit_lite.py summary --window 500 --top 10
```

## Cron example
```bash
*/10 * * * * python3 /root/.openclaw/workspace/skills/reddit-lite/scripts/reddit_lite.py monitor --query "prop trading" --sort new --limit 50 >> /tmp/reddit-prop.log 2>&1
```

## Limits
- This skill is read-only by design.
- Reddit does not reliably expose exact downvotes; `estimated_downs` is derived when possible.

## License
MIT (see `LICENSE`).
