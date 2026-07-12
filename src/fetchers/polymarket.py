#!/usr/bin/env python3
"""
Polymarket fetcher — surfaces events with unusual 24h volume.

Uses the public Gamma API (no auth required). Fetches events (the cards shown on
polymarket.com), not individual per-outcome markets, so aggregated volume ranking
matches the homepage.

Usage:
  python fetchers/polymarket.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone

API_URL = "https://gamma-api.polymarket.com/events"


def fetch_events(limit: int) -> list[dict]:
    url = f"{API_URL}?limit={limit}&order=volume24hr&ascending=false&active=true&closed=false"
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _yes_price(market: dict) -> float | None:
    raw = market.get("outcomePrices")
    if not raw:
        return None
    try:
        prices = json.loads(raw) if isinstance(raw, str) else raw
        return float(prices[0]) if prices else None
    except Exception:
        return None


def normalize(event: dict) -> dict | None:
    title = event.get("title", "").strip()
    if not title:
        return None

    volume_24h = float(event.get("volume24hr", 0) or 0)
    volume_total = float(event.get("volume", 0) or 0)
    slug = event.get("slug", "")
    url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"

    markets = event.get("markets") or []
    # For multi-outcome events (e.g. World Cup Winner), show top options by Yes price.
    # For a single binary market, show its Yes probability.
    outcomes = []
    for m in markets:
        price = _yes_price(m)
        if price is None:
            continue
        label = (m.get("groupItemTitle") or "").strip()
        outcomes.append((label, price))
    outcomes.sort(key=lambda x: x[1], reverse=True)

    if len(markets) == 1 and outcomes:
        prob = round(outcomes[0][1] * 100, 1)
        odds_str = f" — Yes: {prob}%"
    elif outcomes:
        top = [f"{label or 'Yes'}: {round(price * 100, 1)}%" for label, price in outcomes[:3]]
        odds_str = " — " + ", ".join(top)
    else:
        odds_str = ""

    summary = f"24h volume: ${volume_24h:,.0f} | Total: ${volume_total:,.0f}{odds_str}"

    return {
        "title": title,
        "summary": summary,
        "url": url,
        "source": "Polymarket",
        "category": "finance",
        "engagement": volume_24h,
        "engagement_raw": volume_24h,
        "probability": round(outcomes[0][1] * 100, 1) if outcomes else None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Top N events to return (default: 10)")
    args = parser.parse_args()

    print("  Fetching Polymarket top events by 24h volume...", file=sys.stderr)
    try:
        events = fetch_events(100)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for e in events:
        item = normalize(e)
        if item and item["engagement"] > 0:
            results.append(item)

    results = results[:args.limit]
    print(f"  Got {len(results)} events", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
