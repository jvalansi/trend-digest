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

# High-volume mega ETFs included when sorting by raw volume.
HIGH_VOLUME_ETFS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "VOO": "Vanguard S&P 500",
    "VTI": "Total Stock Market",
    "VEA": "Developed Markets ex-US",
    "VWO": "Emerging Markets (Vanguard)",
    "EFA": "MSCI EAFE",
    "AGG": "US Aggregate Bond",
    "LQD": "Investment Grade Corp Bonds",
    "XLF": "Financials Sector",
    "XLK": "Technology Sector",
    "XLV": "Health Care Sector",
    "ARKK": "ARK Innovation",
    "DIA": "Dow Jones Industrial",
}

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
    parser.add_argument("--sort", choices=["ratio", "volume"], default="ratio",
                        help="Sort by anomaly ratio (default) or raw volume")
    args = parser.parse_args()

    if args.sort == "volume":
        all_etfs = {**HIGH_VOLUME_ETFS, **ETFS}
    else:
        all_etfs = ETFS

    tickers = list(all_etfs.keys())
    print(f"  Fetching volume data for {len(tickers)} ETFs...", file=sys.stderr)

    ratios = fetch_volume_ratios(tickers)

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
        label = all_etfs.get(ticker, ticker)
        ratio = item["ratio"]
        today_vol = item["today_volume"]
        avg_vol = item["avg_30d_volume"]

        if args.sort == "volume":
            output.append({
                "title": f"{ticker} ({label}) — {today_vol:,} shares",
                "summary": (
                    f"Traded {today_vol:,} shares today "
                    f"(30-day avg: {avg_vol:,}, ratio: {ratio:.1f}x)."
                ),
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
