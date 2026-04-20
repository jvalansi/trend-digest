#!/usr/bin/env python3
"""
X (Twitter) fetcher — uses Grok via xAI Responses API with x_search tool for real-time posts.

Requires: XAI_API_KEY env var

Usage:
  python fetchers/x.py [--limit N] [--category CATEGORY]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

API_URL = "https://api.x.ai/v1/responses"
MODEL = "grok-4.20-reasoning"


def fetch_trending(limit: int, category: str = "tech") -> list[dict]:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("  ERROR: XAI_API_KEY not set", file=sys.stderr)
        return []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = (
        f"Search X right now and return the top {limit} most viral or trending posts "
        f"in {category} today ({today}). "
        f"For each post return a JSON object with these fields: "
        f"title (post text verbatim or close paraphrase), "
        f"summary (1-2 sentences on why it's trending), "
        f"url (direct https://x.com/USERNAME/status/ID link), "
        f"author (@handle), likes (integer), retweets (integer), "
        f"category (one of: tech, politics, sports, entertainment, science, finance, world, other). "
        f"Use real post IDs from your live X search. "
        f"Respond with a JSON array only — no markdown, no extra text."
    )

    payload = json.dumps({
        "model": MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "x_search"}],
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())

    # Extract text from message output block
    text = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                text += c.get("text", "")

    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def normalize(item: dict) -> dict:
    likes = item.get("likes", 0) or 0
    retweets = item.get("retweets", 0) or 0
    return {
        "title": item.get("title", "").strip(),
        "summary": item.get("summary", "").strip(),
        "url": item.get("url", "https://x.com/explore"),
        "source": "X (via Grok)",
        "category": item.get("category", "other"),
        "author": item.get("author", ""),
        "score": likes + retweets * 2,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of posts to fetch (default: 20)")
    parser.add_argument("--category", default="tech", help="Category to search (default: tech)")
    args = parser.parse_args()

    print(f"  Fetching {args.limit} trending X posts via Grok ({args.category})...", file=sys.stderr)
    try:
        raw = fetch_trending(args.limit, args.category)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    results = [normalize(item) for item in raw if item.get("title")]
    print(f"  Got {len(results)} posts", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
