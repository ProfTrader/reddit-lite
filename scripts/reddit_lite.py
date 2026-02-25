#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

PUBLIC_BASE = "https://www.reddit.com"
DB_PATH = os.path.expanduser("~/.local/share/reddit-lite/reddit-lite.db")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_db(path: str = DB_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen (
            thing_id TEXT PRIMARY KEY,
            seen_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def estimate_downs(ups: Optional[int], upvote_ratio: Optional[float]) -> Optional[int]:
    if ups is None or upvote_ratio is None:
        return None
    if upvote_ratio <= 0 or upvote_ratio >= 1:
        return None
    downs = ups * (1 - upvote_ratio) / upvote_ratio
    return max(0, int(round(downs)))


def ua() -> str:
    return "reddit-lite-readonly/1.0"


def public_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    params = params or {}
    params.setdefault("raw_json", 1)
    params.setdefault("limit", 25)
    params.setdefault("t", int(time.time()))
    url = f"{PUBLIC_BASE}{path}"

    last_err = None
    for attempt in range(1, 4):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": ua()}, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            if attempt < 3:
                time.sleep(1.5 * attempt)
    raise last_err


def normalize_post(d: Dict[str, Any]) -> Dict[str, Any]:
    ups = d.get("ups")
    ratio = d.get("upvote_ratio")
    return {
        "id": d.get("id"),
        "name": d.get("name"),
        "subreddit": d.get("subreddit"),
        "author": d.get("author"),
        "title": d.get("title"),
        "selftext": d.get("selftext"),
        "url": d.get("url"),
        "permalink": f"https://www.reddit.com{d.get('permalink', '')}",
        "created_utc": d.get("created_utc"),
        "score": d.get("score"),
        "ups": ups,
        "upvote_ratio": ratio,
        "estimated_downs": estimate_downs(ups, ratio),
        "num_comments": d.get("num_comments"),
        "total_awards_received": d.get("total_awards_received"),
        "num_crossposts": d.get("num_crossposts"),
        "over_18": d.get("over_18"),
        "is_video": d.get("is_video"),
    }


def normalize_comment(d: Dict[str, Any]) -> Dict[str, Any]:
    ups = d.get("ups")
    ratio = d.get("upvote_ratio")
    return {
        "id": d.get("id"),
        "name": d.get("name"),
        "subreddit": d.get("subreddit"),
        "author": d.get("author"),
        "body": d.get("body"),
        "permalink": f"https://www.reddit.com{d.get('permalink', '')}",
        "created_utc": d.get("created_utc"),
        "score": d.get("score"),
        "ups": ups,
        "upvote_ratio": ratio,
        "estimated_downs": estimate_downs(ups, ratio),
        "total_awards_received": d.get("total_awards_received"),
        "depth": d.get("depth"),
        "parent_id": d.get("parent_id"),
        "link_id": d.get("link_id"),
    }


def flatten_comments(children: List[Dict[str, Any]], out: List[Dict[str, Any]]):
    for c in children:
        if c.get("kind") != "t1":
            continue
        data = c.get("data", {})
        out.append(normalize_comment(data))
        replies = data.get("replies")
        if isinstance(replies, dict):
            nested = replies.get("data", {}).get("children", [])
            flatten_comments(nested, out)


def cmd_subreddit(args):
    payload = public_get(f"/r/{args.name}/{args.sort}.json", {"limit": args.limit})
    posts = [normalize_post(c.get("data", {})) for c in payload.get("data", {}).get("children", []) if c.get("kind") == "t3"]
    print(json.dumps({"mode": "subreddit", "fetched_at": now_utc(), "count": len(posts), "posts": posts}, ensure_ascii=False, indent=2))


def cmd_search(args):
    path = f"/r/{args.subreddit}/search.json" if args.subreddit else "/search.json"
    params = {
        "q": args.query,
        "sort": args.sort,
        "limit": args.limit,
        "restrict_sr": 1 if args.subreddit else 0,
    }
    payload = public_get(path, params)
    posts = [normalize_post(c.get("data", {})) for c in payload.get("data", {}).get("children", []) if c.get("kind") == "t3"]
    print(json.dumps({"mode": "search", "fetched_at": now_utc(), "query": args.query, "count": len(posts), "posts": posts}, ensure_ascii=False, indent=2))


def thread_path_from_input(url_or_id: str) -> str:
    if url_or_id.startswith("http://") or url_or_id.startswith("https://"):
        p = urlparse(url_or_id)
        return p.path.rstrip("/")
    return f"/comments/{url_or_id}"


def cmd_thread(args):
    path = thread_path_from_input(args.url_or_id)
    payload = public_get(f"{path}/.json", {"limit": args.limit_comments, "depth": args.depth})
    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError("Unexpected thread payload")
    post_children = payload[0].get("data", {}).get("children", [])
    post = normalize_post(post_children[0].get("data", {})) if post_children else {}
    comments_listing = payload[1].get("data", {}).get("children", [])
    comments: List[Dict[str, Any]] = []
    flatten_comments(comments_listing, comments)
    print(json.dumps({
        "mode": "thread",
        "fetched_at": now_utc(),
        "post": post,
        "comments_count": len(comments),
        "comments": comments,
    }, ensure_ascii=False, indent=2))


def upsert_seen(conn, items: List[Dict[str, Any]]):
    cur = conn.cursor()
    new_ids = set()
    for item in items:
        thing_id = item.get("name") or item.get("id")
        if not thing_id:
            continue
        exists = cur.execute("SELECT 1 FROM seen WHERE thing_id = ?", (thing_id,)).fetchone()
        if not exists:
            new_ids.add(thing_id)
        cur.execute(
            "INSERT OR REPLACE INTO seen (thing_id, seen_at, payload_json) VALUES (?, ?, ?)",
            (thing_id, now_utc(), json.dumps(item, ensure_ascii=False)),
        )
    conn.commit()
    return new_ids


def cmd_monitor(args):
    if not args.subreddit and not args.query:
        raise RuntimeError("monitor requires --subreddit or --query")

    if args.subreddit and args.query:
        path = f"/r/{args.subreddit}/search.json"
        params = {"q": args.query, "sort": args.sort, "limit": args.limit, "restrict_sr": 1}
    elif args.subreddit:
        path = f"/r/{args.subreddit}/{args.sort}.json"
        params = {"limit": args.limit}
    else:
        path = "/search.json"
        params = {"q": args.query, "sort": args.sort, "limit": args.limit, "restrict_sr": 0}

    payload = public_get(path, params)
    posts = [normalize_post(c.get("data", {})) for c in payload.get("data", {}).get("children", []) if c.get("kind") == "t3"]

    conn = ensure_db(args.db_path)
    new_ids = upsert_seen(conn, posts)
    new_items = [p for p in posts if (p.get("name") or p.get("id")) in new_ids]

    result = {
        "mode": "monitor",
        "fetched_at": now_utc(),
        "total_fetched": len(posts),
        "new_items": len(new_items),
        "items": posts if args.include_all else new_items,
        "db_path": args.db_path,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def compute_hotness(item: Dict[str, Any], now_ts: Optional[float] = None) -> float:
    now_ts = now_ts or time.time()
    created = item.get("created_utc") or now_ts
    age_hours = max(1.0 / 60.0, (now_ts - float(created)) / 3600.0)
    score = float(item.get("score") or 0)
    comments = float(item.get("num_comments") or 0)
    awards = float(item.get("total_awards_received") or 0)
    return (score + comments * 1.5 + awards * 3.0) / (age_hours ** 1.2)


def cmd_summary(args):
    conn = ensure_db(args.db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT payload_json FROM seen ORDER BY seen_at DESC LIMIT ?", (args.window,)).fetchall()
    items = []
    for (payload_json,) in rows:
        try:
            items.append(json.loads(payload_json))
        except Exception:
            continue

    if args.query:
        q = args.query.lower()
        items = [
            x for x in items
            if q in (x.get("title") or "").lower() or q in (x.get("selftext") or "").lower() or q in (x.get("subreddit") or "").lower()
        ]

    ranked = sorted(items, key=lambda x: compute_hotness(x), reverse=True)
    top = ranked[: args.top]
    out = []
    for i, it in enumerate(top, start=1):
        out.append({
            "rank": i,
            "hotness": round(compute_hotness(it), 3),
            "subreddit": it.get("subreddit"),
            "title": it.get("title"),
            "score": it.get("score"),
            "num_comments": it.get("num_comments"),
            "upvote_ratio": it.get("upvote_ratio"),
            "estimated_downs": it.get("estimated_downs"),
            "created_utc": it.get("created_utc"),
            "permalink": it.get("permalink"),
        })

    print(json.dumps({
        "mode": "summary",
        "fetched_at": now_utc(),
        "db_path": args.db_path,
        "candidates": len(items),
        "top_n": len(out),
        "results": out,
    }, ensure_ascii=False, indent=2))


def build_parser():
    p = argparse.ArgumentParser(description="Reddit Lite CLI (read-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("subreddit", help="Fetch latest posts from subreddit")
    s.add_argument("--name", required=True)
    s.add_argument("--sort", default="new", choices=["new", "hot", "top", "rising"])
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_subreddit)

    s = sub.add_parser("search", help="Search Reddit posts")
    s.add_argument("--query", required=True)
    s.add_argument("--subreddit")
    s.add_argument("--sort", default="new", choices=["new", "relevance", "top", "comments"])
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("thread", help="Fetch full thread + nested comments")
    s.add_argument("--url", dest="url_or_id")
    s.add_argument("--id", dest="url_or_id")
    s.add_argument("--depth", type=int, default=8)
    s.add_argument("--limit-comments", type=int, default=500)
    s.set_defaults(func=cmd_thread)

    s = sub.add_parser("monitor", help="Poll + dedupe posts into SQLite")
    s.add_argument("--subreddit")
    s.add_argument("--query")
    s.add_argument("--sort", default="new", choices=["new", "hot", "top", "rising", "relevance", "comments"])
    s.add_argument("--limit", type=int, default=50)
    s.add_argument("--db-path", default=DB_PATH)
    s.add_argument("--include-all", action="store_true", help="Return full fetched set, not just new items")
    s.set_defaults(func=cmd_monitor)

    s = sub.add_parser("summary", help="Rank top opportunities from monitor DB")
    s.add_argument("--db-path", default=DB_PATH)
    s.add_argument("--window", type=int, default=500, help="How many recent stored items to consider")
    s.add_argument("--top", type=int, default=10, help="How many ranked results to return")
    s.add_argument("--query", help="Optional keyword filter before ranking")
    s.set_defaults(func=cmd_summary)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "url_or_id", None) is None and args.cmd == "thread":
        parser.error("thread requires --url or --id")
    try:
        args.func(args)
    except requests.HTTPError as e:
        msg = e.response.text[:500] if e.response is not None else str(e)
        print(json.dumps({"error": "http_error", "detail": msg}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": "runtime_error", "detail": str(e)}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
