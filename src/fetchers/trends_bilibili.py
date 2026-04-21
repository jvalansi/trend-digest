#!/usr/bin/env python3
"""
Bilibili trending fetcher — pulls popular videos from China's largest video platform.

No auth required. Provides a signal for Chinese trending topics.
Titles are in Chinese and will be translated by Claude during curation.

Usage:
  python fetchers/trends_bilibili.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone

from stats import score_items

URL = "https://api.bilibili.com/x/web-interface/popular?ps={limit}&pn=1"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def fetch(limit: int) -> list[dict]:
    url = URL.format(limit=limit)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())

    if data.get("code") != 0:
        raise RuntimeError(f"Bilibili API error: {data.get('message')}")

    items = []
    for video in data["data"]["list"]:
        stat = video.get("stat", {})
        published = None
        if video.get("pubdate"):
            published = datetime.fromtimestamp(video["pubdate"], tz=timezone.utc).isoformat()
        items.append({
            "title": video["title"].strip(),
            "summary": video.get("desc", "").strip()[:300],
            "url": f"https://www.bilibili.com/video/{video['bvid']}",
            "source": "Bilibili Trending",
            "category": "news",
            "views": stat.get("view", 0),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": published,
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Max videos (default: 20)")
    args = parser.parse_args()

    items = fetch(args.limit)
    print(f"  Bilibili Trending: {len(items)} items", file=sys.stderr)
    items = score_items(items, "Bilibili Trending", "views")
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
