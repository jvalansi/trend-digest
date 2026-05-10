#!/usr/bin/env python3
"""
Altmetric top-100 fetcher — scrapes the public Altmetric Explorer top-100 list.

Altmetric scores reflect social media mentions, news coverage, and blog posts
per paper — the best "blowing up right now" signal for science.

No API key required (uses the public explorer page).

Usage:
  python fetchers/altmetric.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

from stats import score_items

EXPLORER_URL = "https://www.altmetric.com/explorer/highlights"


def fetch_top_papers(limit: int) -> list[dict]:
    req = urllib.request.Request(
        EXPLORER_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; trend-digest/1.0)",
            "Accept": "text/html",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="replace")

    # Extract JSON-LD or embedded data if present
    # Fall back to scraping article blocks
    items = []
    # Each paper block contains data-id, title, score
    blocks = re.findall(
        r'data-id="(\d+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?altmetric[_-]score[^>]*>\s*([\d,]+)',
        html, re.DOTALL
    )
    for altmetric_id, title, score_str in blocks[:limit]:
        title = re.sub(r"<[^>]+>", "", title).strip()
        score = int(score_str.replace(",", ""))
        items.append({
            "title": title,
            "summary": "",
            "url": f"https://www.altmetric.com/details/{altmetric_id}",
            "source": "Altmetric",
            "category": "science",
            "score": score,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        })

    if not items:
        print("  WARNING: no items parsed — Altmetric page structure may have changed", file=sys.stderr)

    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of papers (default: 20)")
    args = parser.parse_args()

    print("  Fetching Altmetric top papers...", file=sys.stderr)
    try:
        items = fetch_top_papers(args.limit)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = score_items(items, "Altmetric", "score")
    items = sorted(items, key=lambda x: x["engagement"], reverse=True)[:args.limit]
    print(f"  {len(items)} papers fetched", file=sys.stderr)
    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
