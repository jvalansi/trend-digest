#!/usr/bin/env python3
"""
YouTube fetcher — pulls latest videos from curated channels via playlistItems API.

Uses uploads playlist (1 unit/channel) instead of search (100 units/channel).
Results are cached for 24h to avoid re-fetching within the same day.

Usage:
  python fetchers/youtube.py [--limit N] [--no-cache]

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

DEFAULT_CHANNELS = [
    {"id": "UCsBjURrPoezykLs9EqgamOA", "name": "Fireship"},
    {"id": "UCXuqSBlHAE6Xw-yeJA0Tunw",  "name": "Linus Tech Tips"},
    {"id": "UCbmNph6atAoGfqLoCL_duAg",  "name": "Theo (t3.gg)"},
    {"id": "UC8butISFwT-Wl7EV0hUK0BQ",  "name": "freeCodeCamp"},
    {"id": "UCddiUEpeqJcYeBxX1IVBKvQ",  "name": "ThePrimeagen"},
    {"id": "UCo8bcnLyZH8tBIH9V1mLgqQ",  "name": "ByteByteGo"},
]


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
    """Cache is valid if fetched today (UTC)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return entry.get("date") == today


def get_uploads_playlist_id(channel_id: str) -> str | None:
    """Get the uploads playlist ID for a channel (costs 1 unit)."""
    data = api_get("channels", {"part": "contentDetails", "id": channel_id})
    items = data.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def fetch_playlist_items(playlist_id: str, limit: int) -> list[str]:
    """Fetch video IDs from uploads playlist (costs 1 unit)."""
    data = api_get("playlistItems", {
        "part": "contentDetails",
        "playlistId": playlist_id,
        "maxResults": min(limit, 50),
    })
    return [item["contentDetails"]["videoId"] for item in data.get("items", [])]


def fetch_video_details(video_ids: list[str]) -> list[dict]:
    """Fetch snippet + statistics for a list of video IDs (costs 1 unit per 50)."""
    data = api_get("videos", {
        "part": "snippet,statistics",
        "id": ",".join(video_ids),
        "maxResults": 50,
    })
    return data.get("items", [])


def normalize(item: dict, channel_name: str) -> dict:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    return {
        "title": snippet.get("title", "").strip(),
        "summary": snippet.get("description", "")[:500],
        "url": f"https://www.youtube.com/watch?v={item['id']}",
        "source": f"YouTube / {channel_name}",
        "category": "tech",
        "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": snippet.get("publishedAt"),
        "_view_count": int(stats.get("viewCount", 0) or 0),
    }


def fetch_channel(channel: dict, limit: int, cache: dict) -> list[dict]:
    cid = channel["id"]

    # Get uploads playlist ID (cached)
    if cid not in cache or not cache_valid(cache.get(cid, {})):
        playlist_id = get_uploads_playlist_id(cid)
        if not playlist_id:
            return []
        video_ids = fetch_playlist_items(playlist_id, limit)
        details = fetch_video_details(video_ids)
        items = [normalize(v, channel["name"]) for v in details]
        cache[cid] = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "items": items,
        }
        save_cache(cache)
        return items
    else:
        print(f"  {channel['name']}: using cache", file=sys.stderr)
        return cache[cid]["items"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="Max videos per channel (default: 5)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cache and re-fetch")
    args = parser.parse_args()

    cache = {} if args.no_cache else load_cache()
    results = []

    for channel in DEFAULT_CHANNELS:
        try:
            items = fetch_channel(channel, args.limit, cache)
            results.extend(items)
            print(f"  {channel['name']}: {len(items)} videos", file=sys.stderr)
        except Exception as e:
            print(f"  {channel['name']}: ERROR — {e}", file=sys.stderr)

    for item in results:
        item["score"] = item.pop("_view_count", 0)
    results = score_items(results, "YouTube", "score")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
