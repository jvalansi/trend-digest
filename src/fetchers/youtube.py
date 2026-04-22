#!/usr/bin/env python3
"""
YouTube fetcher — pulls trending videos by category via videos.list?chart=mostPopular.

Category IDs: 25 = News & Politics, 28 = Science & Technology
Results are cached for 6h to avoid burning quota.

Usage:
  python fetchers/youtube.py [--limit N] [--category tech|news] [--no-cache]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from stats import score_items

BASE = "https://www.googleapis.com/youtube/v3"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "youtube_cache.json")

CATEGORY_IDS = {
    "tech": "28",   # Science & Technology
    "news": "25",   # News & Politics
}


def api_get(endpoint: str, params: dict) -> dict:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    params["key"] = api_key
    url = f"{BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


def load_cache() -> dict:
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def cache_valid(entry: dict) -> bool:
    """Cache valid for 6h."""
    try:
        fetched = datetime.fromisoformat(entry["fetched_at"])
        age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
        return age_hours < 6
    except Exception:
        return False


def fetch_trending(category: str, limit: int) -> list[dict]:
    cat_id = CATEGORY_IDS[category]
    data = api_get("videos", {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "videoCategoryId": cat_id,
        "maxResults": min(limit, 50),
        "regionCode": "US",
    })
    items = []
    for v in data.get("items", []):
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})
        items.append({
            "title": snippet.get("title", "").strip(),
            "summary": snippet.get("description", "")[:500],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "source": "YouTube Trending",
            "category": category,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": snippet.get("publishedAt"),
            "score": int(stats.get("viewCount", 0) or 0),
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of videos (default: 20)")
    parser.add_argument("--category", default="tech", choices=["tech", "news"], help="Category (default: tech)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cache and re-fetch")
    args = parser.parse_args()

    cache_key = f"trending_{args.category}"
    cache = {} if args.no_cache else load_cache()

    if cache_key in cache and cache_valid(cache[cache_key]):
        print(f"  YouTube Trending ({args.category}): using cache", file=sys.stderr)
        results = cache[cache_key]["items"]
    else:
        print(f"  Fetching YouTube trending ({args.category})...", file=sys.stderr)
        try:
            results = fetch_trending(args.category, args.limit)
            cache[cache_key] = {"fetched_at": datetime.now(timezone.utc).isoformat(), "items": results}
            save_cache(cache)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    results = score_items(results, f"YouTube Trending ({args.category})", "score")
    print(f"  YouTube Trending ({args.category}): {len(results)} videos", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
