#!/usr/bin/env python3
"""
Reddit trending fetcher — pulls hot posts from news subreddits via residential proxy.

AWS IPs are blocked by Reddit directly; requires REDDIT_PROXY_URL in .env.

Usage:
  python fetchers/trends_reddit.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

from stats import score_items

SUBREDDITS = ["news", "worldnews", "politics"]
BASE = "https://www.reddit.com/r/{sub}/hot.json?limit={limit}"


def load_proxy() -> str | None:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("REDDIT_PROXY_URL="):
                    return line.split("=", 1)[1]
    except Exception:
        pass
    return os.environ.get("REDDIT_PROXY_URL")


def fetch_subreddit(sub: str, limit: int, proxy: str | None) -> list[dict]:
    url = BASE.format(sub=sub, limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})

    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    else:
        opener = urllib.request.build_opener()

    with opener.open(req, timeout=15) as resp:
        data = json.loads(resp.read())

    items = []
    for child in data["data"]["children"]:
        post = child["data"]
        if post.get("stickied") or post.get("is_self") and not post.get("selftext"):
            continue
        published = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc).isoformat()
        items.append({
            "title": post["title"].strip(),
            "summary": post.get("selftext", "")[:300].strip(),
            "url": post.get("url") or f"https://reddit.com{post['permalink']}",
            "source": f"Reddit r/{sub}",
            "category": "news",
            "score": post.get("score", 0),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": published,
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25, help="Posts per subreddit (default: 25)")
    args = parser.parse_args()

    proxy = load_proxy()
    if not proxy:
        print("  Reddit: no REDDIT_PROXY_URL — skipping", file=sys.stderr)
        print("[]")
        return

    all_items = []
    for sub in SUBREDDITS:
        try:
            items = fetch_subreddit(sub, args.limit, proxy)
            items = score_items(items, f"Reddit r/{sub}", "score")
            all_items.extend(items)
            print(f"  Reddit r/{sub}: {len(items)} items", file=sys.stderr)
        except Exception as e:
            print(f"  Reddit r/{sub}: ERROR — {e}", file=sys.stderr)

    print(json.dumps(all_items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
