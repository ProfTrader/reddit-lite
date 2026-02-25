# Contributing

## Setup
- Python 3.10+
- `pip install requests`

## Dev flow
1. Create a branch
2. Make changes in `scripts/reddit_lite.py` or docs
3. Run quick checks:
   ```bash
   python3 scripts/reddit_lite.py subreddit --name python --sort new --limit 2
   python3 scripts/reddit_lite.py summary --window 50 --top 5
   ```
4. Open PR with clear description and sample output

## Rules
- Keep skill read-only
- Keep output JSON stable
- Prefer small, testable changes
