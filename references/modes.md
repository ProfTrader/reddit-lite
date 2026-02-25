# Reddit Lite Modes (Read-Only)

## Read-only data sources

Uses public Reddit JSON endpoints:

- Subreddit listing: `/r/{sub}/{sort}.json`
- Search: `/search.json` or `/r/{sub}/search.json`
- Thread + nested comments: `/{thread_path}/.json`

Use `sort=new` when latest data is required.

## Metrics surfaced

Per post/comment where available:

- `score`
- `ups`
- `upvote_ratio`
- `estimated_downs` (derived from ups + ratio)
- `num_comments` (posts)
- `total_awards_received`
- `num_crossposts`
- `created_utc`
- `permalink`

## Summary mode

Use `summary` to rank opportunity posts from your stored monitor dataset using engagement + recency.

Examples:

```bash
python3 scripts/reddit_lite.py summary --window 500 --top 10
python3 scripts/reddit_lite.py summary --query "prediction markets" --window 1000 --top 15
# or: python3 /path/to/reddit-lite/scripts/reddit_lite.py ...
```

## Cron examples

```bash
*/10 * * * * python3 /path/to/reddit-lite/scripts/reddit_lite.py monitor --subreddit LocalLLaMA --sort new --limit 50 >> /path/to/logs/reddit-monitor.log 2>&1
*/10 * * * * python3 /path/to/reddit-lite/scripts/reddit_lite.py monitor --query "prop trading" --sort new --limit 50 >> /path/to/logs/reddit-monitor.log 2>&1
```

Keep polling >= 5-10 minutes to reduce load and avoid unnecessary retries.
