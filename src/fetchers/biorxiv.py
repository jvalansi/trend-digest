#!/usr/bin/env python3
"""
bioRxiv/medRxiv recent papers fetcher — pulls latest preprints over the last N days.

Uses the bioRxiv/medRxiv details/interval API (date-range endpoint).

Usage:
  python fetchers/biorxiv.py [--limit N] [--server biorxiv|medrxiv] [--days N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from stats import score_items

DETAILS_URL = "https://api.biorxiv.org/details/{server}/{start}/{end}/{cursor}"


def fetch_recent(server: str, limit: int, days: int) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    items = []
    cursor = 0
    seen_dois = set()

    while len(items) < limit * 2:
        url = DETAILS_URL.format(server=server, start=start_str, end=end_str, cursor=cursor)
        req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())

        messages = data.get("messages", [{}])
        status = messages[0].get("status", "") if isinstance(messages, list) else messages.get("status", "")
        if status == "error" or status == "Error":
            print(f"  WARNING: API error: {messages}", file=sys.stderr)
            break

        collection = data.get("collection", [])
        if not collection:
            break

        for paper in collection:
            doi = paper.get("doi", "")
            if doi in seen_dois:
                continue
            seen_dois.add(doi)
            items.append({
                "title": paper.get("title", "").strip(),
                "summary": (paper.get("abstract") or "")[:400].strip(),
                "url": f"https://www.{server}.org/content/{doi}",
                "source": "bioRxiv" if server == "biorxiv" else "medRxiv",
                "category": "science",
                "authors": paper.get("authors", ""),
                "score": 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "published_at": paper.get("date"),
            })

        total = messages[0].get("total", 0) if isinstance(messages, list) else messages.get("total", 0)
        cursor += len(collection)
        if cursor >= int(total or 0) or len(collection) < 30:
            break

    return items[:limit * 2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of papers (default: 20)")
    parser.add_argument("--server", default="biorxiv", choices=["biorxiv", "medrxiv"], help="Server (default: biorxiv)")
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    args = parser.parse_args()

    print(f"  Fetching {args.server} recent papers (last {args.days}d)...", file=sys.stderr)
    try:
        items = fetch_recent(args.server, args.limit, args.days)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = score_items(items, args.server, "score", "citations")
    items = sorted(items, key=lambda x: x.get("published_at") or "", reverse=True)[:args.limit]
    print(f"  {len(items)} papers fetched", file=sys.stderr)
    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
