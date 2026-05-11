#!/usr/bin/env python3
"""
arXiv fetcher — recent papers from q-bio, physics, and cs, sorted by submission date.

Uses the arXiv Atom API (free, no key required).

Usage:
  python fetchers/arxiv.py [--limit N] [--days N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from stats import score_items

CATEGORIES = "cat:q-bio.* OR cat:physics.* OR cat:cs.*"


def fetch_papers(days: int, limit: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y%m%d")
    query = f"({CATEGORIES}) AND submittedDate:[{since}000000 TO 99991231235959]"

    params = urllib.parse.urlencode({
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": min(limit * 4, 200),
    })
    url = f"https://export.arxiv.org/api/query?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})

    with urllib.request.urlopen(req, timeout=30) as r:
        resp = r.read().decode()

    entries = re.findall(r"<entry>(.*?)</entry>", resp, re.DOTALL)
    items = []
    for e in entries:
        title_m = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
        summary_m = re.search(r"<summary>(.*?)</summary>", e, re.DOTALL)
        id_m = re.search(r"<id>(.*?)</id>", e, re.DOTALL)
        published_m = re.search(r"<published>(.*?)</published>", e)
        cats = re.findall(r'<category term="([^"]+)"', e)
        authors = re.findall(r"<name>(.*?)</name>", e)

        if not title_m or not id_m:
            continue

        arxiv_url = id_m.group(1).strip()
        title = re.sub(r"\s+", " ", title_m.group(1)).strip()
        summary = re.sub(r"\s+", " ", summary_m.group(1)).strip()[:400] if summary_m else ""
        published = published_m.group(1)[:10] if published_m else None

        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += " et al."

        primary_cat = cats[0] if cats else ""

        items.append({
            "title": title,
            "summary": summary,
            "url": arxiv_url,
            "source": "arXiv",
            "category": "science",
            "authors": author_str,
            "arxiv_category": primary_cat,
            "score": 0,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": published,
        })

    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of papers to return (default: 20)")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    args = parser.parse_args()

    print(f"  Fetching arXiv papers (last {args.days}d, cats: q-bio/physics/cs)...", file=sys.stderr)
    try:
        items = fetch_papers(args.days, args.limit)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = score_items(items, "arXiv", "score")
    items = sorted(items, key=lambda x: x.get("published_at") or "", reverse=True)
    items = items[:args.limit]

    print(f"  {len(items)} papers fetched", file=sys.stderr)
    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
