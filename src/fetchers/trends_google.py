#!/usr/bin/env python3
"""
Google Trends fetcher — pulls trending searches from the official public RSS
feed at trends.google.com/trending/rss?geo=XX. Each item includes an approx
traffic figure and one or more news headlines picked by Google, so no
separate news lookup is needed.

Usage:
  python fetchers/trends_google.py [--geo GEO] [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from stats import score_items

HT_NS = "https://trends.google.com/trending/rss"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def parse_traffic(text: str | None) -> float:
    """Turn '2,000+' / '20K+' / '1M+' into a float."""
    if not text:
        return 0.0
    s = text.strip().replace(",", "").replace("+", "").upper()
    m = re.match(r"^([\d.]+)\s*([KM]?)$", s)
    if not m:
        return 0.0
    n = float(m.group(1))
    mult = {"K": 1_000, "M": 1_000_000}.get(m.group(2), 1)
    return n * mult


def fetch(geo: str, limit: int) -> list[dict]:
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    r = requests.get(url, headers={"user-agent": USER_AGENT}, timeout=20)
    if r.status_code != 200 or not r.text.strip().startswith("<?xml"):
        print(f"  ERROR: {geo} returned {r.status_code}", file=sys.stderr)
        return []

    root = ET.fromstring(r.text)
    now = datetime.now(timezone.utc).isoformat()
    items = []
    for item in root.findall(".//item"):
        query = (item.findtext("title") or "").strip()
        if not query:
            continue
        traffic = parse_traffic(item.findtext(f"{{{HT_NS}}}approx_traffic"))
        try:
            pub = parsedate_to_datetime(item.findtext("pubDate") or "")
            published = pub.astimezone(timezone.utc).isoformat() if pub else None
        except Exception:
            published = None

        news = item.find(f"{{{HT_NS}}}news_item")
        headline = (news.findtext(f"{{{HT_NS}}}news_item_title") or "").strip() if news is not None else ""
        article_url = (news.findtext(f"{{{HT_NS}}}news_item_url") or "").strip() if news is not None else ""
        link = article_url or f"https://trends.google.com/trending?geo={geo}&q={urllib.parse.quote(query)}"

        items.append({
            "title": query,
            "summary": headline,
            "url": link,
            "source": "Google Trends",
            "category": "news",
            "traffic": traffic,
            "fetched_at": now,
            "published_at": published,
        })
        if len(items) >= limit:
            break
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
