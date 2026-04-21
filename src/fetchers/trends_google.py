#!/usr/bin/env python3
"""
Google Trends fetcher — pulls daily trending searches via the public RSS feed.

Each trending topic includes related news articles and approximate traffic volume.

Usage:
  python fetchers/trends_google.py [--geo GEO] [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

import feedparser
from stats import score_items

FEED_URL = "https://trends.google.com/trending/rss?geo={geo}"


def parse_traffic(approx: str) -> float:
    """Convert '200000+' or '1000+' to a float."""
    try:
        return float(re.sub(r"[^\d]", "", approx))
    except Exception:
        return 0.0


def fetch(geo: str, limit: int) -> list[dict]:
    url = FEED_URL.format(geo=geo)
    parsed = feedparser.parse(url)
    items = []
    for entry in parsed.entries[:limit]:
        traffic_tag = entry.get("ht_approx_traffic", "0")
        traffic = parse_traffic(traffic_tag)

        # Related news article — fields are flat on the entry
        url_out = entry.get("ht_news_item_url", "")
        summary = entry.get("ht_news_item_title", "")

        published = None
        if entry.get("published_parsed"):
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

        items.append({
            "title": entry.get("title", "").strip(),
            "summary": summary,
            "url": url_out or f"https://trends.google.com/trending?geo={geo}",
            "source": "Google Trends",
            "category": "news",
            "traffic": traffic,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": published,
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--geo", default="US", help="Country code (default: US)")
    parser.add_argument("--limit", type=int, default=20, help="Max trends to fetch (default: 20)")
    args = parser.parse_args()

    items = fetch(args.geo, args.limit)
    print(f"  Google Trends ({args.geo}): {len(items)} items", file=sys.stderr)
    items = score_items(items, "Google Trends", "traffic")
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
