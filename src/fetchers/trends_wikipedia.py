#!/usr/bin/env python3
"""
Wikipedia Pageviews fetcher — pulls the most-read articles from the previous day.

High pageviews on a Wikipedia article is a strong signal that something newsworthy
happened around that topic.

Usage:
  python fetchers/trends_wikipedia.py [--limit N] [--date YYYY-MM-DD]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from stats import score_items

BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access"

SKIP = {
    "Main_Page", "Special:Search", "Special:Random", "Special:Export",
    "Wikipedia:Featured_pictures", "Portal:Current_events",
}


def fetch(date: str, limit: int) -> list[dict]:
    y, m, d = date.split("-")
    url = f"{BASE}/{y}/{m}/{d}"
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())

    articles = data["items"][0]["articles"]
    items = []
    for art in articles:
        title = art["article"]
        if title in SKIP or title.startswith("Special:"):
            continue
        display = title.replace("_", " ")
        wiki_url = f"https://en.wikipedia.org/wiki/{title}"
        items.append({
            "title": display,
            "summary": f"Trending on Wikipedia: {art['views']:,} views",
            "url": wiki_url,
            "source": "Wikipedia Trending",
            "category": "news",
            "views": art["views"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        })
        if len(items) >= limit:
            break
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Max articles (default: 20)")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()

    date = args.date or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    items = fetch(date, args.limit)
    print(f"  Wikipedia Trending ({date}): {len(items)} items", file=sys.stderr)
    items = score_items(items, "Wikipedia Trending", "views")
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
