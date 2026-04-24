#!/usr/bin/env python3
"""
Hugging Face daily papers fetcher — pulls community-upvoted arXiv papers from HF.

Usage:
  python fetchers/hf_papers.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone

from stats import score_items

API_URL = "https://huggingface.co/api/daily_papers?limit={limit}"


def fetch_papers(limit: int) -> list[dict]:
    url = API_URL.format(limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())

    items = []
    for entry in data:
        paper = entry.get("paper", entry)
        arxiv_id = paper.get("id", "")
        summary = paper.get("ai_summary") or paper.get("summary", "")
        published = paper.get("publishedAt") or entry.get("publishedAt")
        items.append({
            "title": paper.get("title", "").strip(),
            "summary": summary[:400].strip(),
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "https://huggingface.co/papers",
            "source": "HF Papers",
            "category": "tech",
            "upvotes": paper.get("upvotes", 0) or 0,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": published,
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of papers to fetch (default: 20)")
    args = parser.parse_args()

    print(f"  Fetching {args.limit} HF daily papers...", file=sys.stderr)
    try:
        items = fetch_papers(args.limit)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = score_items(items, "HF Papers", "upvotes")
    items = sorted(items, key=lambda x: x["engagement"], reverse=True)
    print(f"  Got {len(items)} papers", file=sys.stderr)
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
