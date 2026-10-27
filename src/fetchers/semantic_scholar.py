#!/usr/bin/env python3
"""
Semantic Scholar fetcher — papers from the last year ranked by citations gained
over the last week (see citation_velocity.py), not by total citations.

Usage:
  python fetchers/semantic_scholar.py [--limit N] [--days N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from citation_velocity import rank_by_gain

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,citationCount,publicationDate,externalIds,authors"
QUERIES = {
    "tech": ["artificial intelligence", "machine learning", "large language model", "deep learning"],
    "science": ["biology", "physics", "neuroscience", "climate science", "quantum computing", "genomics"],
}


def fetch_papers(days: int, limit: int, mode: str) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_range = f"{since}:{today}"

    seen_ids = set()
    items = []

    for query in QUERIES.get(mode, QUERIES["tech"]):
        url = (
            f"{BASE_URL}?query={urllib.parse.quote(query)}"
            f"&fields={FIELDS}"
            f"&publicationDateOrYear={date_range}"
            f"&limit=100"
            f"&sort=citationCount:desc"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
        data = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = 2 ** attempt * 5
                    print(f"  WARNING: rate limited on '{query}', waiting {wait}s (attempt {attempt+1})", file=sys.stderr)
                    time.sleep(wait)
                else:
                    print(f"  WARNING: query '{query}' failed: {e}", file=sys.stderr)
                    break
            except Exception as e:
                print(f"  WARNING: query '{query}' failed: {e}", file=sys.stderr)
                break
        if data is None:
            time.sleep(1)
            continue

        for paper in data.get("data", []):
            paper_id = paper.get("paperId", "")
            if not paper_id or paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)

            arxiv_id = (paper.get("externalIds") or {}).get("ArXiv", "")
            url_out = (
                f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id
                else f"https://www.semanticscholar.org/paper/{paper_id}"
            )
            authors = paper.get("authors") or []
            author_str = ", ".join(a.get("name", "") for a in authors[:3])
            if len(authors) > 3:
                author_str += " et al."

            items.append({
                "title": paper.get("title", "").strip(),
                "summary": (paper.get("abstract") or "")[:400].strip(),
                "url": url_out,
                "source": "Semantic Scholar",
                "category": "tech",
                "authors": author_str,
                "paper_id": paper_id,
                "total_citations": paper.get("citationCount") or 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "published_at": paper.get("publicationDate"),
            })

        time.sleep(1)  # respect 1 req/sec unauthenticated limit

    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of papers to return (default: 20)")
    parser.add_argument("--days", type=int, default=365, help="Look back N days (default: 365)")
    parser.add_argument("--mode", default="tech", choices=["tech", "science"], help="Query set (default: tech)")
    args = parser.parse_args()

    print(f"  Fetching top Semantic Scholar papers (last {args.days}d, mode={args.mode})...", file=sys.stderr)
    try:
        items = fetch_papers(args.days, args.limit, args.mode)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Rank by citations gained this week, not total, so the same papers don't win daily
    items = rank_by_gain(items, "Semantic Scholar", "paper_id", "total_citations")
    items = sorted(items, key=lambda x: x["engagement"], reverse=True)
    items = items[:args.limit]

    print(f"  {len(items)} papers fetched", file=sys.stderr)
    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
