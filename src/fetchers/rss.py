#!/usr/bin/env python3
"""
RSS fetcher — pulls latest headlines from a list of feeds.

Usage:
  python fetchers/rss.py [--feeds FEEDS_FILE] [--limit N] [--category CATEGORY]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import feedparser
from stats import score_items

# Default tech feeds — can be overridden via --feeds
DEFAULT_FEEDS = [
    {"source": "The Verge",       "url": "https://www.theverge.com/rss/index.xml",               "category": "tech"},
    {"source": "TechCrunch",      "url": "https://techcrunch.com/feed/",                          "category": "tech"},
    {"source": "Ars Technica",    "url": "https://feeds.arstechnica.com/arstechnica/index",       "category": "tech"},
    {"source": "Wired",           "url": "https://www.wired.com/feed/rss",                        "category": "tech"},
    {"source": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/",                "category": "tech"},
    {"source": "VentureBeat",     "url": "https://venturebeat.com/feed/",                        "category": "tech"},
    {"source": "Engadget",        "url": "https://www.engadget.com/rss.xml",                     "category": "tech"},
    {"source": "ZDNet",           "url": "https://www.zdnet.com/news/rss.xml",                   "category": "tech"},

    # News feeds — top 15 by Similarweb traffic (news & media category, March 2026)
    {"source": "Yahoo Japan",     "url": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",                "category": "news"},
    {"source": "Globo",           "url": "https://g1.globo.com/rss/g1/",                                     "category": "news"},
    {"source": "New York Times",  "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",       "category": "news"},
    {"source": "BBC News",        "url": "http://feeds.bbci.co.uk/news/rss.xml",                             "category": "news"},
    {"source": "CNN",             "url": "http://rss.cnn.com/rss/edition.rss",                               "category": "news"},
    {"source": "The Guardian",    "url": "https://www.theguardian.com/world/rss",                            "category": "news"},
    {"source": "Times of India",  "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",      "category": "news"},
    {"source": "Google News",     "url": "https://news.google.com/rss",                                      "category": "news"},
    {"source": "Fox News",        "url": "https://moxie.foxnews.com/google-publisher/latest.xml",            "category": "news"},
    {"source": "UOL",             "url": "https://rss.uol.com.br/feed/noticias.xml",                        "category": "news"},
    {"source": "Infobae",         "url": "https://www.infobae.com/arc/outboundfeeds/rss/",                  "category": "news"},
]


def fetch_feed(feed_def: dict, limit: int) -> list[dict]:
    parsed = feedparser.parse(feed_def["url"])
    items = []
    for entry in parsed.entries[:limit]:
        # Normalize published date
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

        summary = entry.get("summary", "") or ""
        # Strip HTML tags from summary if present
        if "<" in summary:
            import re
            summary = re.sub(r"<[^>]+>", "", summary).strip()

        items.append({
            "title": entry.get("title", "").strip(),
            "summary": summary[:500],
            "url": entry.get("link", ""),
            "source": feed_def["source"],
            "category": feed_def["category"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": published,
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feeds", help="JSON file with feed definitions (list of {source, url, category})")
    parser.add_argument("--limit", type=int, default=10, help="Max items per feed (default: 10)")
    parser.add_argument("--category", help="Filter to a specific category")
    args = parser.parse_args()

    if args.feeds:
        with open(args.feeds) as f:
            feeds = json.load(f)
    else:
        feeds = DEFAULT_FEEDS

    if args.category:
        feeds = [f for f in feeds if f.get("category") == args.category]

    results = []
    for feed_def in feeds:
        try:
            items = fetch_feed(feed_def, args.limit)
            results.extend(items)
            print(f"  {feed_def['source']}: {len(items)} items", file=sys.stderr)
        except Exception as e:
            print(f"  {feed_def['source']}: ERROR — {e}", file=sys.stderr)

    # RSS has no engagement signal — assign 0 for all items
    for item in results:
        item["engagement"] = 0.0
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
