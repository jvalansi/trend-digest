#!/usr/bin/env python3
"""
Top 10 S&P 500 companies by market cap value creation per decade.
Decades: 1985-1995, 1995-2005, 2005-2015, 2015-2025

For 2005-2015 and 2015-2025, reads from already-computed CSVs.
For 1985-1995 and 1995-2005, fetches a curated set of likely leaders
one ticker at a time with long delays to avoid rate limiting.

Output: data/sp500_value_creation_by_decade.csv
"""

import csv
import math
import sys
import time
from datetime import date, timedelta

import yfinance as yf

SP500_CLASSIFIED = "/home/ubuntu/trend-digest/data/sp500_classified.csv"
CSV_2015_2025    = "/home/ubuntu/trend-digest/data/sp500_value_creation.csv"
CSV_2005_2015    = "/home/ubuntu/trend-digest/data/sp500_value_creation_2005_2015.csv"
OUTPUT = "/home/ubuntu/trend-digest/data/sp500_value_creation_by_decade.csv"

FIELDNAMES = ["decade", "rank", "ticker", "name", "sector",
              "enabling_tech", "underlying_science",
              "start_mcap_b", "end_mcap_b", "value_created_b"]

# Curated candidates for older decades — companies still in S&P 500
# that were publicly traded in those eras and likely to be top value creators
OLDER_DECADE_CANDIDATES = [
    # Tech / computing
    "MSFT", "AAPL", "IBM", "INTC", "QCOM", "TXN", "ADI", "HPQ",
    # Pharma / biotech
    "JNJ", "MRK", "PFE", "ABBV", "AMGN", "GILD", "BMY", "ABT",
    # Finance
    "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "BLK",
    # Energy
    "XOM", "CVX", "COP", "SLB", "HAL", "OXY",
    # Consumer / industrial
    "WMT", "KO", "PG", "MCD", "HD", "NKE", "GE", "HON", "MMM",
    "DE", "CAT", "LMT", "BA", "RTX",
    # Telecom
    "T", "VZ",
    # Retail / media
    "AMZN", "GOOGL", "GOOG", "META", "NFLX", "DIS", "CMCSA",
]


def get_price_on_date(ticker: str, target_date: str, retries: int = 3) -> float | None:
    end_dt = date.fromisoformat(target_date) + timedelta(days=12)
    for attempt in range(retries):
        try:
            df = yf.download(
                [ticker],
                start=target_date,
                end=end_dt.isoformat(),
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if df.empty:
                return None
            val = df["Close"].iloc[0]
            if hasattr(val, "__len__"):
                val = val.iloc[0]
            return float(val) if not math.isnan(float(val)) else None
        except Exception as e:
            if "Rate" in str(e) and attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
                continue
            return None
    return None


def get_fast_info(ticker: str, retries: int = 3) -> tuple[float, float]:
    """Returns (market_cap, last_price) or (None, None)."""
    for attempt in range(retries):
        try:
            fi = yf.Ticker(ticker).fast_info
            mc = getattr(fi, "market_cap", None)
            lp = getattr(fi, "last_price", None)
            if mc and lp and mc > 0 and lp > 0:
                return float(mc), float(lp)
            return None, None
        except Exception as e:
            if "Rate" in str(e) and attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
                continue
            return None, None
    return None, None


def load_existing_decades() -> list[dict]:
    rows = []
    for path, decade_label, start_col, end_col in [
        (CSV_2005_2015, "2005-2015", "mcap_start", "mcap_end"),
        (CSV_2015_2025, "2015-2025", "mcap_2015", "mcap_now"),
    ]:
        with open(path) as f:
            companies = list(csv.DictReader(f))
        scored = [c for c in companies if float(c["value_created"]) > 0]
        scored.sort(key=lambda c: float(c["value_created"]), reverse=True)
        for i, c in enumerate(scored[:10]):
            rows.append({
                "decade": decade_label,
                "rank": i + 1,
                "ticker": c["ticker"],
                "name": c["name"],
                "sector": c["sector"],
                "enabling_tech": c.get("enabling_tech", "none"),
                "underlying_science": c.get("underlying_science", "none"),
                "start_mcap_b": round(float(c[start_col]), 1),
                "end_mcap_b": round(float(c[end_col]), 1),
                "value_created_b": round(float(c["value_created"]), 1),
            })
    return rows


def fetch_older_decades(meta_map: dict) -> list[dict]:
    OLDER_DECADES = [
        ("1985-1995", "1985-01-02", "1995-01-02"),
        ("1995-2005", "1995-01-02", "2005-01-03"),
    ]

    candidates = [t for t in OLDER_DECADE_CANDIDATES if t in meta_map]
    print(f"Fetching data for {len(candidates)} candidates...", file=sys.stderr)

    # Get current market cap + price for ratio calculation
    print("  Step 1: current market caps...", file=sys.stderr)
    mcap_now: dict[str, float] = {}
    price_now: dict[str, float] = {}
    for ticker in candidates:
        mc, lp = get_fast_info(ticker)
        if mc and lp:
            mcap_now[ticker] = mc
            price_now[ticker] = lp
        time.sleep(1.5)
    print(f"  Got {len(mcap_now)} current market caps", file=sys.stderr)

    # Get historical prices for each date endpoint
    all_dates = sorted(set(d for _, s, e in OLDER_DECADES for d in (s, e)))
    price_hist: dict[tuple[str, str], float] = {}
    for dt in all_dates:
        print(f"  Step 2: prices @ {dt}...", file=sys.stderr)
        for ticker in candidates:
            p = get_price_on_date(ticker, dt)
            if p:
                price_hist[(ticker, dt)] = p
            time.sleep(1.5)
        got = sum(1 for (t, d) in price_hist if d == dt)
        print(f"    Got {got}/{len(candidates)} prices", file=sys.stderr)

    rows = []
    for decade_label, start_date, end_date in OLDER_DECADES:
        results = []
        for ticker in candidates:
            mc = mcap_now.get(ticker)
            pc = price_now.get(ticker)
            ps = price_hist.get((ticker, start_date))
            pe = price_hist.get((ticker, end_date))
            c = meta_map[ticker]
            if not (mc and pc and ps and pe and pc > 0):
                continue
            start_mcap = mc * (ps / pc) / 1e9
            end_mcap = mc * (pe / pc) / 1e9
            value_created = end_mcap - start_mcap
            results.append({
                "decade": decade_label,
                "rank": 0,
                "ticker": ticker,
                "name": c["name"],
                "sector": c["sector"],
                "enabling_tech": c.get("enabling_tech", "none"),
                "underlying_science": c.get("underlying_science", "none"),
                "start_mcap_b": round(start_mcap, 1),
                "end_mcap_b": round(end_mcap, 1),
                "value_created_b": round(value_created, 1),
            })
        results.sort(key=lambda x: x["value_created_b"], reverse=True)
        for i, r in enumerate(results[:10]):
            r["rank"] = i + 1
        rows.extend(results[:10])

        print(f"\n=== {decade_label} TOP 10 ===", file=sys.stderr)
        for r in results[:10]:
            print(f"  #{r['rank']:2d} {r['ticker']:6} {r['name'][:30]:30} "
                  f"+${r['value_created_b']:,.0f}B  |  {r['underlying_science'][:40]}", file=sys.stderr)

    return rows


def main():
    print("Loading existing decade data (2005-2015, 2015-2025)...", file=sys.stderr)
    existing_rows = load_existing_decades()

    for decade in ["2005-2015", "2015-2025"]:
        decade_rows = [r for r in existing_rows if r["decade"] == decade]
        print(f"\n=== {decade} TOP 10 ===", file=sys.stderr)
        for r in decade_rows:
            print(f"  #{r['rank']:2d} {r['ticker']:6} {r['name'][:30]:30} "
                  f"+${r['value_created_b']:,.0f}B  |  {r['underlying_science'][:40]}", file=sys.stderr)

    with open(SP500_CLASSIFIED) as f:
        companies = list(csv.DictReader(f))
    meta_map = {c["ticker"]: c for c in companies}

    new_rows = fetch_older_decades(meta_map)

    decade_order = {"1985-1995": 0, "1995-2005": 1, "2005-2015": 2, "2015-2025": 3}
    all_rows = sorted(new_rows + existing_rows,
                      key=lambda r: (decade_order.get(r["decade"], 99), r["rank"]))

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} rows to {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
