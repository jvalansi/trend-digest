#!/usr/bin/env python3
"""
Hacker News fetcher — pulls top/new/best stories via the Firebase REST API.

Usage:
  python fetchers/hn.py [--feed top|new|best|ask|show] [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from stats import score_items

BASE = "https://hacker-news.firebaseio.com/v0"
FEEDS = {
    "top":  f"{BASE}/topstories.json",
    "new":  f"{BASE}/newstories.json",
    "best": f"{BASE}/beststories.json",
    "ask":  f"{BASE}/askstories.json",
    "show": f"{BASE}/showstories.json",
}


def fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


def fetch_item(item_id: int) -> dict | None:
    try:
        return fetch_json(f"{BASE}/item/{item_id}.json")
    except Exception:
        return None


def normalize(item: dict) -> dict:
    published = None
    if item.get("time"):
        published = datetime.fromtimestamp(item["time"], tz=timezone.utc).isoformat()
    return {
        "title": item.get("title", "").strip(),
        "summary": item.get("text", "") or "",
        "url": item.get("url") or f"https://news.ycombinator.com/item?id={item['id']}",
        "source": "Hacker News",
        "category": "tech",
        "score": item.get("score", 0),
        "comments": item.get("descendants", 0),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": published,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", default="top", choices=FEEDS.keys(), help="Which feed to fetch (default: top)")
    parser.add_argument("--limit", type=int, default=30, help="Number of stories to fetch (default: 30)")
    args = parser.parse_args()

    ids = fetch_json(FEEDS[args.feed])[:args.limit]
    print(f"  Fetching {len(ids)} items from HN {args.feed}...", file=sys.stderr)

    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_item, i): i for i in ids}
        for future in as_completed(futures):
            item = future.result()
            if item and item.get("type") == "story" and item.get("title"):
                results.append(normalize(item))

    results.sort(key=lambda x: x["score"], reverse=True)
    results = score_items(results, "Hacker News", "score")
    print(f"  Got {len(results)} stories", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
