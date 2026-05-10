#!/usr/bin/env python3
"""
bioRxiv/medRxiv most-read fetcher — pulls top accessed preprints over the last month.

Uses the bioRxiv/medRxiv REST API usage endpoint which returns papers ranked by
access count — a genuine trending signal independent of citation lag.

Usage:
  python fetchers/biorxiv.py [--limit N] [--server biorxiv|medrxiv]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone

from stats import score_items

BASE_URL = "https://api.biorxiv.org/usage/{server}/0/{limit}"


def fetch_most_read(server: str, limit: int) -> list[dict]:
    url = BASE_URL.format(server=server, limit=limit * 2)
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())

    items = []
    for paper in data.get("usage", [])[:limit]:
        doi = paper.get("doi", "")
        items.append({
            "title": paper.get("title", "").strip(),
            "summary": paper.get("abstract", "")[:400].strip(),
            "url": f"https://www.{server}.org/content/{doi}",
            "source": "bioRxiv" if server == "biorxiv" else "medRxiv",
            "category": "science",
            "authors": paper.get("authors", ""),
            "score": paper.get("abstract_views", 0) + paper.get("full_text_views", 0),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": paper.get("date"),
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of papers (default: 20)")
    parser.add_argument("--server", default="biorxiv", choices=["biorxiv", "medrxiv"], help="Server (default: biorxiv)")
    args = parser.parse_args()

    print(f"  Fetching {args.server} most-read papers...", file=sys.stderr)
    try:
        items = fetch_most_read(args.server, args.limit)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = score_items(items, args.server, "score")
    items = sorted(items, key=lambda x: x["engagement"], reverse=True)[:args.limit]
    print(f"  {len(items)} papers fetched", file=sys.stderr)
    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
