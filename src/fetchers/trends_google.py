#!/usr/bin/env python3
"""
Google Trends fetcher — scrapes trending searches via the internal batchexecute API
using a headless browser to match what appears on trends.google.com/trending.

Usage:
  python fetchers/trends_google.py [--geo GEO] [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser

from stats import score_items

NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def fetch_headline(query: str) -> str:
    try:
        url = NEWS_RSS.format(query=urllib.parse.quote(query))
        feed = feedparser.parse(url)
        if feed.entries:
            return feed.entries[0].title
    except Exception:
        pass
    return ""


def fetch(geo: str, limit: int) -> list[dict]:
    from playwright.sync_api import sync_playwright

    trend_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(resp):
            if "batchexecute" in resp.url and "i0OFE" in resp.url:
                try:
                    trend_data["body"] = resp.text()
                except Exception:
                    pass

        page.on("response", on_response)
        page.goto(
            f"https://trends.google.com/trending?geo={geo}&hl=en-US",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        page.wait_for_timeout(5000)
        browser.close()

    body = trend_data.get("body", "")
    if not body:
        return []

    lines = body.splitlines()
    # Response format: )]}'\n\n<size>\n<json>\n...
    # The JSON line is at index 3
    json_line = next((l for l in lines if l.startswith("[[")), "")
    if not json_line:
        return []

    outer = json.loads(json_line)
    inner = json.loads(outer[0][2])
    trends = inner[1] or []

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
            items[idx]["summary"] = future.result()

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
