#!/usr/bin/env python3
"""
Polymarket fetcher — surfaces events with unusual 24h volume.

Ranks by 24h volume relative to the event's own prior daily average, so the
always-busy flagship markets don't top the list every day. Events younger than
a week, individual games, rolling series and date ladders, and markets that
were dormant before today are skipped, since they have no meaningful baseline.

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
from datetime import datetime, timedelta, timezone

API_URL = "https://gamma-api.polymarket.com/events"
MIN_VOLUME_24H = 100_000  # ignore thin markets, where a single trade is a "surge"
MIN_PRIOR_DAILY = 1_000   # markets dormant until resolution day have no meaningful baseline
MIN_AGE_DAYS = 7
SKIP_TAGS = {"games", "recurring"}  # matches (all volume on game day), rolling weekly/monthly series
MAX_END_DATES = 10        # date ladders ("on...?", "by...?") shift volume to the expiring rung daily


def fetch_events(limit: int) -> list[dict]:
    events = []
    for offset in range(0, limit, 100):  # the API returns at most 100 per page
        url = f"{API_URL}?limit=100&offset={offset}&order=volume24hr&ascending=false&active=true&closed=false"
        req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = json.loads(resp.read())
        events += page
        if len(page) < 100:
            break
    # ranks shift between pages, so an event can appear on both
    return list({e.get("id"): e for e in events}.values())[:limit]


def _yes_price(market: dict) -> float | None:
    raw = market.get("outcomePrices")
    if not raw:
        return None
    try:
        prices = json.loads(raw) if isinstance(raw, str) else raw
        return float(prices[0]) if prices else None
    except Exception:
        return None


def volume_surge(event: dict, now: datetime) -> float | None:
    """24h volume over the average daily volume of the 6 days before it, or None
    if the event is too new or too thin to judge."""
    if SKIP_TAGS & {t.get("slug") for t in event.get("tags") or []}:
        return None
    if len({m.get("endDate") for m in event.get("markets") or []}) >= MAX_END_DATES:
        return None
    created = event.get("createdAt")
    if not created or datetime.fromisoformat(created.replace("Z", "+00:00")) > now - timedelta(days=MIN_AGE_DAYS):
        return None
    v24 = float(event.get("volume24hr", 0) or 0)
    prior = (float(event.get("volume1wk", 0) or 0) - v24) / 6
    if v24 < MIN_VOLUME_24H or prior < MIN_PRIOR_DAILY:
        return None
    return v24 / prior


def normalize(event: dict, surge: float) -> dict | None:
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

    top_label = outcomes[0][0] if outcomes else ""
    is_binary = len(markets) == 1
    if is_binary and outcomes:
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
        "engagement": surge,
        "engagement_raw": round(surge, 1),
        "engagement_label": "× daily avg volume",
        "probability": round(outcomes[0][1] * 100, 1) if outcomes else None,
        "probability_label": "Yes" if is_binary else (top_label or "Yes"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Top N events to return (default: 10)")
    args = parser.parse_args()

    print("  Fetching Polymarket events with surging 24h volume...", file=sys.stderr)
    try:
        events = fetch_events(200)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    results = []
    for e in events:
        surge = volume_surge(e, now)
        item = normalize(e, surge) if surge else None
        if item:
            results.append(item)

    results = sorted(results, key=lambda x: x["engagement"], reverse=True)[:args.limit]
    print(f"  Got {len(results)} events", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
