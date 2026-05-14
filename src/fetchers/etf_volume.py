#!/usr/bin/env python3
"""
ETF volume anomaly fetcher — detects ETFs trading at unusually high volume vs. their average.

Uses FMP /v3/quotes/etf (one API call, all ETFs, includes volume + avgVolume).
Filters to US-listed ETFs. Reports anomalies where volume/avgVolume exceeds threshold.

Usage:
  python fetchers/etf_volume.py [--limit N] [--min-ratio F] [--sort ratio|volume]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("  ERROR: requests not installed", file=sys.stderr)
    sys.exit(1)

US_EXCHANGES = {"AMEX", "NASDAQ", "NYSE", "BATS", "NYSEArca"}
FMP_BASE = "https://financialmodelingprep.com/api"


def fetch_etf_quotes(fmp_key: str) -> list[dict]:
    resp = requests.get(f"{FMP_BASE}/v3/quotes/etf?apikey={fmp_key}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--min-ratio", type=float, default=1.5)
    parser.add_argument("--sort", choices=["ratio", "volume"], default="ratio")
    args = parser.parse_args()

    fmp_key = os.environ.get("FMP_API_KEY", "")
    if not fmp_key:
        print("  ERROR: FMP_API_KEY not set", file=sys.stderr)
        print("[]")
        return

    print("  Fetching ETF quotes from FMP...", file=sys.stderr)
    quotes = fetch_etf_quotes(fmp_key)
    print(f"  Total ETFs: {len(quotes)}", file=sys.stderr)

    us_quotes = [q for q in quotes if q.get("exchange") in US_EXCHANGES]
    print(f"  US-listed ETFs: {len(us_quotes)}", file=sys.stderr)

    ratios = []
    for q in us_quotes:
        vol = q.get("volume") or 0
        avg_vol = q.get("avgVolume") or 0
        if avg_vol < 10_000 or vol <= 0:
            continue
        ratios.append({
            "ticker": q["symbol"],
            "name": q.get("name", q["symbol"]),
            "today_volume": int(vol),
            "avg_volume": int(avg_vol),
            "ratio": round(vol / avg_vol, 2),
        })

    if args.sort == "volume":
        ranked = sorted(ratios, key=lambda x: x["today_volume"], reverse=True)[:args.limit]
    else:
        anomalies = [r for r in ratios if r["ratio"] >= args.min_ratio]
        ranked = sorted(anomalies, key=lambda x: x["ratio"], reverse=True)[:args.limit]
        print(f"  Found {len(anomalies)} ETFs with ratio >= {args.min_ratio}x", file=sys.stderr)

    now = datetime.now(timezone.utc).isoformat()
    output = []
    for item in ranked:
        ticker = item["ticker"]
        name = item["name"]
        ratio = item["ratio"]
        today_vol = item["today_volume"]
        avg_vol = item["avg_volume"]

        if args.sort == "volume":
            output.append({
                "title": f"{ticker} ({name}) — {today_vol:,} shares",
                "summary": f"Traded {today_vol:,} shares today (avg: {avg_vol:,}, ratio: {ratio:.1f}x).",
                "url": f"https://finance.yahoo.com/quote/{ticker}",
                "source": "ETF Volume",
                "category": "finance",
                "engagement": today_vol,
                "engagement_raw": today_vol,
                "fetched_at": now,
                "published_at": now,
            })
        else:
            output.append({
                "title": f"{ticker} ({name}) — {ratio:.1f}x normal volume",
                "summary": (
                    f"Trading at {ratio:.1f}x its average volume today "
                    f"({today_vol:,} vs avg {avg_vol:,})."
                ),
                "url": f"https://finance.yahoo.com/quote/{ticker}",
                "source": "ETF Volume",
                "category": "finance",
                "engagement": round(ratio, 2),
                "engagement_raw": ratio,
                "fetched_at": now,
                "published_at": now,
            })

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
