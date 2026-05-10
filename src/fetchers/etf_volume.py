#!/usr/bin/env python3
"""
ETF volume anomaly fetcher — detects ETFs trading at unusually high volume vs. their 30-day average.

Uses yfinance (no API key required).

Usage:
  python fetchers/etf_volume.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    print("  ERROR: yfinance not installed", file=sys.stderr)
    sys.exit(1)

# Thematic/country/commodity ETFs with geopolitical signal value.
# Excludes mega-funds (SPY, QQQ, IWM) that spike constantly for routine reasons.
ETFS = {
    # Defense & geopolitics
    "ITA": "US Aerospace & Defense",
    "XAR": "Aerospace & Defense (SPDR)",
    "PPA": "Defense & Aerospace",
    # Energy & commodities
    "XLE": "US Energy Sector",
    "OIH": "Oil Services",
    "USO": "Crude Oil",
    "UNG": "Natural Gas",
    "GLD": "Gold",
    "SLV": "Silver",
    "WEAT": "Wheat",
    "CORN": "Corn",
    # Geopolitical regions
    "EWJ": "Japan",
    "EWZ": "Brazil",
    "EWG": "Germany",
    "EWY": "South Korea",
    "EWI": "Italy",
    "EWT": "Taiwan",
    "INDA": "India",
    "EEM": "Emerging Markets",
    "EWQ": "France",
    "EZA": "South Africa",
    "TUR": "Turkey",
    "EWW": "Mexico",
    # Thematic
    "HACK": "Cybersecurity",
    "NLR": "Nuclear Energy",
    "REMX": "Rare Earth Metals",
    "LIT": "Lithium & Battery",
    "BOTZ": "Robotics & AI",
    "SMH": "Semiconductors",
    # Rates & credit stress
    "HYG": "High Yield Bonds",
    "TLT": "Long-Term Treasuries",
    "EMB": "Emerging Market Bonds",
}


def fetch_volume_ratios(tickers: list[str]) -> list[dict]:
    results = []
    data = yf.download(tickers, period="35d", interval="1d", progress=False, auto_adjust=True)

    if data.empty:
        print("  ERROR: yfinance returned no data", file=sys.stderr)
        return []

    volume = data["Volume"] if "Volume" in data.columns else data.xs("Volume", axis=1, level=0)

    for ticker in tickers:
        try:
            series = volume[ticker].dropna()
            if len(series) < 5:
                continue
            today_vol = float(series.iloc[-1])
            avg_30d = float(series.iloc[:-1].tail(30).mean())
            if avg_30d <= 0:
                continue
            ratio = today_vol / avg_30d
            results.append({
                "ticker": ticker,
                "today_volume": int(today_vol),
                "avg_30d_volume": int(avg_30d),
                "ratio": round(ratio, 2),
            })
        except Exception as e:
            print(f"  {ticker}: ERROR — {e}", file=sys.stderr)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Top N ETFs to return (default: 10)")
    parser.add_argument("--min-ratio", type=float, default=1.5, help="Minimum volume ratio to include (default: 1.5)")
    args = parser.parse_args()

    tickers = list(ETFS.keys())
    print(f"  Fetching volume data for {len(tickers)} ETFs...", file=sys.stderr)

    ratios = fetch_volume_ratios(tickers)
    anomalies = [r for r in ratios if r["ratio"] >= args.min_ratio]
    anomalies = sorted(anomalies, key=lambda x: x["ratio"], reverse=True)[:args.limit]

    print(f"  Found {len(anomalies)} ETFs with ratio >= {args.min_ratio}x", file=sys.stderr)

    now = datetime.now(timezone.utc).isoformat()
    output = []
    for item in anomalies:
        ticker = item["ticker"]
        label = ETFS.get(ticker, ticker)
        ratio = item["ratio"]
        today_vol = item["today_volume"]
        avg_vol = item["avg_30d_volume"]
        output.append({
            "title": f"{ticker} ({label}) — {ratio:.1f}x normal volume",
            "summary": (
                f"Trading at {ratio:.1f}x its 30-day average volume today "
                f"({today_vol:,} vs avg {avg_vol:,}). "
                f"Unusual activity may signal geopolitical or macro movement."
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
