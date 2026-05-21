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
import subprocess
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("  ERROR: requests not installed", file=sys.stderr)
    sys.exit(1)

US_EXCHANGES = {"AMEX", "NASDAQ", "NYSE", "BATS", "NYSEArca"}
FMP_BASE = "https://financialmodelingprep.com/api"
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "etf_descriptions.json")


def fetch_etf_quotes(fmp_key: str) -> list[dict]:
    resp = requests.get(f"{FMP_BASE}/v3/quotes/etf?apikey={fmp_key}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_etf_description(ticker: str, fmp_key: str) -> str:
    """Return a short description of what the ETF tracks, or empty string on failure."""
    try:
        resp = requests.get(f"{FMP_BASE}/v3/profile/{ticker}?apikey={fmp_key}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list):
            desc = data[0].get("description", "")
            first_sentence = desc.split(".")[0].strip()
            return first_sentence[:120] if first_sentence else ""
    except Exception:
        pass
    return ""


def load_desc_cache() -> dict:
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_desc_cache(cache: dict) -> None:
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  WARNING: could not save description cache: {e}", file=sys.stderr)


def generate_descriptions_claude(items: list[dict]) -> dict:
    """Call Claude CLI (subscription mode) to generate plain-English descriptions for a list of ETFs.
    Returns dict of ticker → description string.
    """
    if not items:
        return {}

    lines = ["For each ETF below, write one plain-English sentence (max 20 words) explaining what it tracks or bets on. Return ONLY a JSON object mapping ticker to description, no other text.\n"]
    for item in items:
        lines.append(f"{item['ticker']}: {item['name']}")
    prompt = "\n".join(lines)

    claude_path = os.environ.get("CLAUDE_PATH", "/home/ubuntu/.local/bin/claude")
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    try:
        result = subprocess.run(
            [claude_path, "-p", prompt, "--output-format", "text", "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=60, env=env,
        )
        text = result.stdout.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        if result.returncode != 0:
            print(f"  WARNING: Claude exited {result.returncode}: {result.stderr[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"  WARNING: Claude description generation failed: {e}", file=sys.stderr)
    return {}


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

    cache = load_desc_cache()
    need_lookup = [item for item in ranked if item["ticker"] not in cache]

    if need_lookup:
        print(f"  Generating descriptions via Claude for {len(need_lookup)} tickers...", file=sys.stderr)
        claude_descs = generate_descriptions_claude(need_lookup)
        for ticker, desc in claude_descs.items():
            if desc:
                cache[ticker] = desc
                print(f"    {ticker} (Claude): {desc[:60]}", file=sys.stderr)

        save_desc_cache(cache)

    descriptions = {item["ticker"]: cache.get(item["ticker"], "") for item in ranked}

    now = datetime.now(timezone.utc).isoformat()
    output = []
    for item in ranked:
        ticker = item["ticker"]
        name = item["name"]
        ratio = item["ratio"]
        today_vol = item["today_volume"]
        avg_vol = item["avg_volume"]
        desc = descriptions.get(ticker, "")
        desc_suffix = f" {desc}." if desc else ""

        if args.sort == "volume":
            output.append({
                "title": f"{ticker} ({name}) — {today_vol:,} shares",
                "summary": f"Traded {today_vol:,} shares today (avg: {avg_vol:,}, ratio: {ratio:.1f}x).{desc_suffix}",
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
                    f"({today_vol:,} vs avg {avg_vol:,}).{desc_suffix}"
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
