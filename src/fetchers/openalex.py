#!/usr/bin/env python3
"""
OpenAlex trending preprints fetcher — preprints from the last N days sorted by citation count.

Uses the OpenAlex API (free, no key required).

Usage:
  python fetchers/openalex.py [--limit N] [--days N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from stats import score_items

BASE_URL = "https://api.openalex.org/works"

SCIENCE_CONCEPTS = [
    "biology", "medicine", "neuroscience", "physics", "chemistry",
    "genomics", "ecology", "climate", "immunology", "epidemiology",
]


def fetch_preprints(days: int, limit: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    seen_ids = set()
    items = []

    for concept in SCIENCE_CONCEPTS:
        if len(items) >= limit * 3:
            break

        params = urllib.parse.urlencode({
            "filter": f"type:preprint,from_publication_date:{since}",
            "search": concept,
            "sort": "cited_by_count:desc",
            "per-page": 25,
            "select": "id,title,abstract_inverted_index,cited_by_count,publication_date,primary_location,authorships",
            "mailto": "trend-digest@example.com",
        })
        url = f"{BASE_URL}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"  WARNING: concept '{concept}' failed: {e}", file=sys.stderr)
            continue

        for work in data.get("results", []):
            work_id = work.get("id", "")
            if not work_id or work_id in seen_ids:
                continue
            seen_ids.add(work_id)

            loc = work.get("primary_location") or {}
            landing = loc.get("landing_page_url") or ""
            url_out = landing or work_id

            # Reconstruct abstract from inverted index
            inv = work.get("abstract_inverted_index") or {}
            summary = ""
            if inv:
                word_positions = [(pos, word) for word, positions in inv.items() for pos in positions]
                word_positions.sort()
                summary = " ".join(w for _, w in word_positions)[:400]

            authors = work.get("authorships") or []
            author_names = [a.get("author", {}).get("display_name", "") for a in authors[:3] if a.get("author")]
            author_str = ", ".join(filter(None, author_names))
            if len(authors) > 3:
                author_str += " et al."

            items.append({
                "title": (work.get("title") or "").strip(),
                "summary": summary.strip(),
                "url": url_out,
                "source": "OpenAlex",
                "category": "science",
                "authors": author_str,
                "citations": work.get("cited_by_count") or 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "published_at": work.get("publication_date"),
            })

    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of papers to return (default: 20)")
    parser.add_argument("--days", type=int, default=75, help="Look back N days (default: 75)")
    args = parser.parse_args()

    print(f"  Fetching OpenAlex trending preprints (last {args.days}d)...", file=sys.stderr)
    try:
        items = fetch_preprints(args.days, args.limit)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = score_items(items, "OpenAlex", "citations")
    items = sorted(items, key=lambda x: x.get("citations", 0), reverse=True)

    # Dedup by URL
    seen_urls: set[str] = set()
    unique = []
    for item in items:
        u = item.get("url", "")
        if u not in seen_urls:
            seen_urls.add(u)
            unique.append(item)

    unique = unique[:args.limit]
    print(f"  {len(unique)} preprints fetched", file=sys.stderr)
    print(json.dumps(unique, ensure_ascii=False))


if __name__ == "__main__":
    main()
