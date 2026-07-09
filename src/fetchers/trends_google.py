#!/usr/bin/env python3
"""
Google Trends fetcher — scrapes trending searches from trends.google.com/trending
by parsing the inlined AF_initDataCallback('ds:0') payload from the page HTML.

Usage:
  python fetchers/trends_google.py [--geo GEO] [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser
import requests

from stats import score_items

NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DS0_RE = re.compile(
    r"AF_initDataCallback\(\{key: 'ds:0'[^,]*, hash: '[^']*'[^,]*, data:(.*?), sideChannel:",
    re.DOTALL,
)


def fetch_trending_page(geo: str) -> list:
    """Return the raw trend rows from the /trending page for the given geo, or []."""
    r = requests.get(
        f"https://trends.google.com/trending?geo={geo}&hl=en-US",
        headers={"user-agent": USER_AGENT, "accept-language": "en-US,en;q=0.9"},
        timeout=20,
    )
    m = DS0_RE.search(r.text)
    if not m:
        return []
    data = json.loads(m.group(1))
    return (data[1] if len(data) > 1 else None) or []


def fetch_headline(query: str) -> tuple[str, str]:
    try:
        rss_url = NEWS_RSS.format(query=urllib.parse.quote(query))
        feed = feedparser.parse(rss_url)
        if feed.entries:
            e = feed.entries[0]
            return e.title, e.get("link", "")
    except Exception:
        pass
    return "", ""


def fetch(geo: str, limit: int) -> list[dict]:
    trends = fetch_trending_page(geo)

    now = datetime.now(timezone.utc).isoformat()
    items = []
    for t in trends[:limit]:
        query = t[0]
        traffic = t[6] if len(t) > 6 and t[6] else 0
        timestamp = t[3][0] if len(t) > 3 and t[3] else None
        published = (
            datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            if timestamp
            else None
        )
        url = f"https://trends.google.com/trending?geo={geo}&q={urllib.parse.quote(query)}"

        items.append({
            "title": query,
            "summary": "",
            "url": url,
            "source": "Google Trends",
            "category": "news",
            "traffic": float(traffic),
            "fetched_at": now,
            "published_at": published,
        })

    # Fetch top news headline for each trend in parallel
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_headline, item["title"]): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            idx = futures[future]
            headline, article_url = future.result()
            items[idx]["summary"] = headline
            if article_url:
                items[idx]["url"] = article_url

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
