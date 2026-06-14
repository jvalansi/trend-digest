#!/usr/bin/env python3
"""
Polymarket fetcher — surfaces markets with unusual volume or large odds shifts.

Uses the public Gamma API (no auth required).

Usage:
  python fetchers/polymarket.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone

API_URL = "https://gamma-api.polymarket.com/markets"


def fetch_markets(limit: int) -> list[dict]:
    url = f"{API_URL}?limit=100&order=volume24hr&ascending=false&active=true&closed=false"
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def normalize(market: dict) -> dict | None:
    question = market.get("question", "").strip()
    if not question:
        return None

    volume_24h = float(market.get("volume24hr", 0) or 0)
    volume_total = float(market.get("volume", 0) or 0)
    slug = market.get("slug", "")
    url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"

    # Get probability from outcomes
    outcomes_raw = market.get("outcomePrices") or market.get("outcomes", "[]")
    try:
        if isinstance(outcomes_raw, str):
            prices = json.loads(outcomes_raw)
        else:
            prices = outcomes_raw
        # First outcome is typically "Yes"
        prob = round(float(prices[0]) * 100, 1) if prices else None
    except Exception:
        prob = None

    prob_str = f" — Yes: {prob}%" if prob is not None else ""
    summary = (
        f"24h volume: ${volume_24h:,.0f} | Total: ${volume_total:,.0f}{prob_str}"
    )

    return {
        "title": question,
        "summary": summary,
        "url": url,
        "source": "Polymarket",
        "category": "finance",
        "engagement": volume_24h,
        "engagement_raw": volume_24h,
        "probability": prob,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Top N markets to return (default: 10)")
    args = parser.parse_args()

    print("  Fetching Polymarket top markets by 24h volume...", file=sys.stderr)
    try:
        markets = fetch_markets(100)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for m in markets:
        item = normalize(m)
        if item and item["engagement"] > 0:
            results.append(item)

    results = results[:args.limit]
    print(f"  Got {len(results)} markets", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
