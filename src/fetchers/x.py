#!/usr/bin/env python3
"""
X (Twitter) fetcher — uses Grok (xAI API) to retrieve trending topics from X.

Requires: XAI_API_KEY env var

Usage:
  python fetchers/x.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

API_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-3"


def fetch_trending(limit: int) -> list[dict]:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("  ERROR: XAI_API_KEY not set", file=sys.stderr)
        return []

    prompt = f"""Return the top {limit} trending topics on X (Twitter) right now.
For each topic, provide:
- title: the topic or headline (concise)
- summary: 1-2 sentence description of what's being discussed
- url: a relevant x.com search or trending URL (use https://x.com/search?q=TOPIC&f=live)
- category: one of: tech, politics, sports, entertainment, science, finance, world, other

Respond with a JSON array only, no other text. Example format:
[{{"title": "...", "summary": "...", "url": "...", "category": "..."}}]"""

    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    content = data["choices"][0]["message"]["content"].strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)


def normalize(item: dict) -> dict:
    return {
        "title": item.get("title", "").strip(),
        "summary": item.get("summary", "").strip(),
        "url": item.get("url", "https://x.com/explore"),
        "source": "X (via Grok)",
        "category": item.get("category", "other"),
        "score": 0,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of trending topics (default: 20)")
    args = parser.parse_args()

    print(f"  Fetching {args.limit} trending X topics via Grok...", file=sys.stderr)
    try:
        raw = fetch_trending(args.limit)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    results = [normalize(item) for item in raw if item.get("title")]
    print(f"  Got {len(results)} topics", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
