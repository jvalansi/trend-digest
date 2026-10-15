#!/usr/bin/env python3
"""
Google Trends fetcher — pulls the past-24h "Trending now" list (the same data
as trends.google.com/trending) via the web UI's batchexecute endpoint, sorted
by search volume. The public RSS feed only lists the ~10 most recently started
trends, so it misses the big ones; it's used here just for news headlines.

Usage:
  python fetchers/trends_google.py [--geo GEO] [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

from stats import score_items

HT_NS = "https://trends.google.com/trending/rss"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


BATCH_URL = "https://trends.google.com/_/TrendsUi/data/batchexecute"
RPC_ID = "i0OFE"  # "Trending now" list used by the trends.google.com/trending web UI


def fetch_headlines(geo: str) -> dict[str, tuple[str, str]]:
    """Query -> (headline, article_url) from the RSS feed.

    The RSS feed only carries the ~10 most recently started trends, so it
    only covers a few of the high-volume ones; it is used for headlines only.
    """
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        r = requests.get(url, headers={"user-agent": USER_AGENT}, timeout=20)
        root = ET.fromstring(r.text)
    except Exception as e:
        print(f"  WARN: RSS headlines for {geo} failed: {e}", file=sys.stderr)
        return {}
    out = {}
    for item in root.findall(".//item"):
        news = item.find(f"{{{HT_NS}}}news_item")
        if news is None:
            continue
        query = (item.findtext("title") or "").strip().lower()
        out[query] = (
            (news.findtext(f"{{{HT_NS}}}news_item_title") or "").strip(),
            (news.findtext(f"{{{HT_NS}}}news_item_url") or "").strip(),
        )
    return out


def fetch_trending(geo: str, hours: int = 24) -> list[list]:
    """Raw trend rows for the past `hours`, as shown on the web UI.

    Row layout (undocumented): [0] query, [3] [start_ts], [4] [end_ts] or
    null if still active, [6] search volume, [8] growth %, [9] related queries.
    """
    req = [[[RPC_ID, json.dumps([None, None, geo, 0, "en-US", hours, 1]), None, "generic"]]]
    r = requests.post(
        BATCH_URL,
        data={"f.req": json.dumps(req)},
        headers={"user-agent": USER_AGENT},
        timeout=20,
    )
    r.raise_for_status()
    # Response is ")]}'" followed by JSON chunks; the payload is on the wrb.fr line
    for line in r.text.splitlines():
        if line.startswith('[["wrb.fr"'):
            payload = json.loads(line)[0][2]
            return json.loads(payload)[1] or []
    raise ValueError("no wrb.fr payload in batchexecute response")


def fetch(geo: str, limit: int) -> list[dict]:
    try:
        rows = fetch_trending(geo)
    except Exception as e:
        print(f"  ERROR: {geo} batchexecute failed: {e}", file=sys.stderr)
        return []
    headlines = fetch_headlines(geo)

    rows = [r for r in rows if r and r[0]]
    rows.sort(key=lambda r: r[6] or 0, reverse=True)

    now = datetime.now(timezone.utc).isoformat()
    items = []
    for row in rows[:limit]:
        query = row[0].strip()
        started = row[3][0] if row[3] else None
        published = datetime.fromtimestamp(started, timezone.utc).isoformat() if started else None
        headline, article_url = headlines.get(query.lower(), ("", ""))
        if not headline:
            related = [q for q in (row[9] or []) if q.lower() != query.lower()]
            headline = ", ".join(related[:5])
        link = article_url or f"https://trends.google.com/trending?geo={geo}&q={urllib.parse.quote(query)}"

        items.append({
            "title": query,
            "summary": headline,
            "url": link,
            "source": "Google Trends",
            "category": "news",
            "traffic": float(row[6] or 0),
            "fetched_at": now,
            "published_at": published,
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--geo", default="US", help="Country code (default: US)")
    parser.add_argument("--limit", type=int, default=20, help="Max trends to fetch (default: 20)")
    args = parser.parse_args()

    items = fetch(args.geo, args.limit)
    print(f"  Google Trends ({args.geo}): {len(items)} items", file=sys.stderr)
    items = score_items(items, "Google Trends", "traffic", "searches")
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
