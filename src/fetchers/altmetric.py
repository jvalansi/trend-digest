#!/usr/bin/env python3
"""
CrossRef rising papers fetcher — science papers gaining citations fastest.

Uses the CrossRef REST API (no key required) to pull the most-cited papers
registered in the last N days, then ranks them by citations gained over the
last week (see citation_velocity.py) rather than by total.

Usage:
  python fetchers/altmetric.py [--limit N] [--days N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from citation_velocity import rank_by_gain

BASE_URL = "https://api.crossref.org/works"
# Science-focused queries to filter for relevant papers
SCIENCE_QUERIES = [
    "biology genetics genomics",
    "neuroscience brain",
    "physics quantum materials",
    "climate change ecology environment",
    "medicine clinical trial vaccine",
]
MAILTO = "trend-digest@example.com"


def fetch_top_papers(limit: int, days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    seen_dois = set()
    items = []

    for query in SCIENCE_QUERIES:
        params = urllib.parse.urlencode({
            "query": query,
            "sort": "is-referenced-by-count",
            "order": "desc",
            # created = DOI registration; "published" can be a future print-issue date
            "filter": f"from-created-date:{since},type:journal-article",
            "rows": 100,
            "select": "title,author,DOI,URL,is-referenced-by-count,published,abstract",
            "mailto": MAILTO,
        })
        url = f"{BASE_URL}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": f"trend-digest/1.0 (mailto:{MAILTO})"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"  WARNING: CrossRef query '{query}' failed: {e}", file=sys.stderr)
            time.sleep(1)
            continue

        for paper in data.get("message", {}).get("items", []):
            doi = paper.get("DOI", "")
            if not doi or doi in seen_dois:
                continue
            seen_dois.add(doi)

            titles = paper.get("title") or []
            title = titles[0] if titles else ""

            authors = paper.get("author") or []
            author_str = ", ".join(
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in authors[:3]
            )
            if len(authors) > 3:
                author_str += " et al."

            abstracts = paper.get("abstract") or ""
            # CrossRef abstracts may contain JATS XML tags
            import re
            summary = re.sub(r"<[^>]+>", "", abstracts)[:400].strip()

            pub = paper.get("published") or {}
            date_parts = pub.get("date-parts", [[]])[0] if pub.get("date-parts") else []
            published_at = "-".join(str(p) for p in date_parts) if date_parts else None

            paper_url = paper.get("URL") or (f"https://doi.org/{doi}" if doi else "")

            items.append({
                "title": title.strip(),
                "summary": summary,
                "url": paper_url,
                "doi": doi,
                "source": "Altmetric",
                "category": "science",
                "authors": author_str,
                "score": paper.get("is-referenced-by-count") or 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "published_at": published_at,
            })

        time.sleep(0.5)

    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of papers (default: 20)")
    parser.add_argument("--days", type=int, default=365, help="Days to look back (default: 365)")
    args = parser.parse_args()

    print("  Fetching top science papers via CrossRef...", file=sys.stderr)
    try:
        items = fetch_top_papers(args.limit, args.days)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = rank_by_gain(items, "Altmetric", "doi", "score")
    items = sorted(items, key=lambda x: x["engagement"], reverse=True)[:args.limit]
    print(f"  {len(items)} papers fetched", file=sys.stderr)
    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
