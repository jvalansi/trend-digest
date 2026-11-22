#!/usr/bin/env python3
"""
ETF volume anomaly fetcher — detects ETFs trading at unusually high volume vs. their average.

Uses FMP /v3/quotes/etf (one API call, all ETFs, includes volume + avgVolume).
Filters to US-listed ETFs. Reports anomalies where volume/avgVolume exceeds threshold.
The quote's avgVolume is wrong for some tickers (LITX: 27,700 vs ~3M/day in FMP's own
history), so the top candidates are re-scored against a baseline from daily history.

Usage:
  python fetchers/etf_volume.py [--limit N] [--min-ratio F] [--sort ratio|volume]
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:
    import requests
except ImportError:
    print("  ERROR: requests not installed", file=sys.stderr)
    sys.exit(1)

US_EXCHANGES = {"AMEX", "NASDAQ", "NYSE", "BATS", "NYSEArca"}
FMP_BASE = "https://financialmodelingprep.com/api"
BASELINE_DAYS = 20
MIN_AVG_VOLUME = 10_000  # thinner ETFs "spike" on a single block trade
MAX_RECHECKS = 60  # one history call each
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "etf_descriptions.json")


def fetch_etf_quotes(fmp_key: str) -> list[dict]:
    resp = requests.get(f"{FMP_BASE}/v3/quotes/etf?apikey={fmp_key}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fresh_quotes(quotes: list[dict], max_age_days: int = 4) -> list[dict]:
    """Drop quotes that stopped updating. FMP keeps serving the last quote of
    delisted ETFs (e.g. TVIX, frozen since 2020), whose stale volume looks like a
    huge anomaly. Age is measured from the newest quote, so weekends don't matter."""
    newest = max((q.get("timestamp") or 0 for q in quotes), default=0)
    return [q for q in quotes if (q.get("timestamp") or 0) >= newest - max_age_days * 86400]


def baseline_volume(hist: list[dict], before: str, days: int = BASELINE_DAYS) -> float | None:
    """Mean daily volume of the `days` sessions strictly before `before` (YYYY-MM-DD),
    or None with under 5 sessions of history (too new to call anything a spike)."""
    vols = [h["volume"] for h in hist if h["date"] < before and h.get("volume")][:days]
    return sum(vols) / len(vols) if len(vols) >= 5 else None


def fetch_baseline(ticker: str, before: str, fmp_key: str) -> float | None:
    try:
        resp = requests.get(f"{FMP_BASE}/v3/historical-price-full/{ticker}",
                            params={"timeseries": BASELINE_DAYS + 5, "apikey": fmp_key}, timeout=15)
        resp.raise_for_status()
        return baseline_volume(resp.json().get("historical", []), before)
    except Exception:
        return None


def rescore(candidates: list[dict], fetch) -> list[dict]:
    """Replace FMP's avgVolume with the history baseline from fetch(candidate); drop tickers
    without one or too thin."""
    with ThreadPoolExecutor(8) as pool:
        baselines = list(pool.map(fetch, candidates))
    missing = sum(1 for b in baselines if b is None)
    if missing:
        print(f"  WARNING: no usable history for {missing}/{len(candidates)} candidates", file=sys.stderr)
    out = []
    for c, base in zip(candidates, baselines):
        if base and base >= MIN_AVG_VOLUME:
            out.append({**c, "avg_volume": int(base), "ratio": round(c["today_volume"] / base, 2)})
    return out


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
    # ANTHROPIC_API_KEY in .env is stale and overrides the subscription login
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "CLAUDECODE")}

    try:
        result = subprocess.run(
            [claude_path, "-p", prompt, "--output-format", "text", "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=60, env=env,
        )
        text = result.stdout.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(text[start:end])
            if isinstance(parsed, dict):
                return {k: v for k, v in parsed.items() if isinstance(v, str)}
        if result.returncode != 0:
            print(f"  WARNING: Claude exited {result.returncode}: stdout={text[:200]!r} stderr={result.stderr[:200]!r}", file=sys.stderr)
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

    us_quotes = [q for q in fresh_quotes(quotes) if q.get("exchange") in US_EXCHANGES]
    print(f"  US-listed ETFs: {len(us_quotes)}", file=sys.stderr)

    ratios = []
    for q in us_quotes:
        vol = q.get("volume") or 0
        avg_vol = q.get("avgVolume") or 0
        if avg_vol < MIN_AVG_VOLUME or vol <= 0:
            continue
        ratios.append({
            "ticker": q["symbol"],
            "name": q.get("name", q["symbol"]),
            "today_volume": int(vol),
            "avg_volume": int(avg_vol),
            "ratio": round(vol / avg_vol, 2),
            # ET, so an after-hours quote (past midnight UTC) still dates to its session
            "session": datetime.fromtimestamp(q["timestamp"], ZoneInfo("America/New_York")).date().isoformat(),
        })

    if args.sort == "volume":
        ranked = sorted(ratios, key=lambda x: x["today_volume"], reverse=True)[:args.limit]
    else:
        anomalies = sorted((r for r in ratios if r["ratio"] >= args.min_ratio), key=lambda x: x["ratio"], reverse=True)
        print(f"  Found {len(anomalies)} ETFs with ratio >= {args.min_ratio}x", file=sys.stderr)
        rescored = [r for r in rescore(anomalies[:MAX_RECHECKS],
                                             lambda c: fetch_baseline(c["ticker"], c["session"], fmp_key)) if r["ratio"] >= args.min_ratio]
        print(f"  {len(rescored)}/{min(len(anomalies), MAX_RECHECKS)} still >= {args.min_ratio}x "
              f"against {BASELINE_DAYS}-day history", file=sys.stderr)
        ranked = sorted(rescored, key=lambda x: x["ratio"], reverse=True)[:args.limit]

    cache = load_desc_cache()
    need_lookup = [item for item in ranked if item["ticker"] not in cache]

    if need_lookup:
        # Try FMP profile descriptions first (authoritative)
        for item in need_lookup:
            ticker = item["ticker"]
            desc = fetch_etf_description(ticker, fmp_key)
            if desc:
                cache[ticker] = desc
                print(f"    {ticker} (FMP): {desc[:60]}", file=sys.stderr)

        # Fall back to Claude for any still missing
        still_missing = [item for item in need_lookup if item["ticker"] not in cache]
        if still_missing:
            print(f"  Generating descriptions via Claude for {len(still_missing)} tickers...", file=sys.stderr)
            claude_descs = generate_descriptions_claude(still_missing)
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
        desc_prefix = f"{desc} " if desc else ""

        if args.sort == "volume":
            output.append({
                "title": f"{ticker} ({name}) — {today_vol:,} shares",
                "summary": f"{desc_prefix}Traded {today_vol:,} shares last session (avg: {avg_vol:,}, ratio: {ratio:.1f}x).",
                "url": f"https://finance.yahoo.com/quote/{ticker}",
                "source": "ETF Volume",
                "category": "finance",
                "engagement": today_vol,
                "engagement_raw": today_vol,
                "engagement_label": "shares last session",
                "fetched_at": now,
                "published_at": now,
            })
        else:
            output.append({
                "title": f"{ticker} ({name}) — {ratio:.1f}x normal volume",
                "summary": (
                    f"{desc_prefix}Volume spiked to {ratio:.1f}x above average "
                    f"({today_vol:,} vs avg {avg_vol:,} shares)."
                ),
                "url": f"https://finance.yahoo.com/quote/{ticker}",
                "source": "ETF Volume",
                "category": "finance",
                "engagement": round(ratio, 2),
                "engagement_raw": ratio,
                "engagement_label": "× normal volume",
                "fetched_at": now,
                "published_at": now,
            })

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
