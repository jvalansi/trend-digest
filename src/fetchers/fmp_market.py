#!/usr/bin/env python3
"""
Market fetcher (FMP) — what moved, why, and what's coming.

Parts (one aggregate section each):
  snapshot  one item: indices, VIX, 2Y/10Y yields, oil, gold, dollar, BTC, best/worst sector
  movers    US large caps (≥ $10B) ranked by |last session's move| / their own 60-day daily volatility,
            each with the latest FMP headlines for the ticker as the "why"
  calendar  one item: upcoming session's large-cap earnings and high-impact US macro releases

Run outside market hours (the digest runs pre-open), so quotes carry the last full session.

Usage:
  python fetchers/fmp_market.py --part snapshot|movers|calendar [--limit N] [--min-z F]
"""

import argparse
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from etf_volume import fresh_quotes

FMP = "https://financialmodelingprep.com/api"
MIN_MARKET_CAP = 10_000_000_000
# Preferreds and exchangeable debentures (CMS-PB, CCZ) pass the market-cap screen
# through their parent but trade thinly; real large caps clear this easily.
MIN_DOLLAR_VOLUME = 20_000_000

# Auto-generated 13F-filing and price-recap articles, which never explain a move
SPAM_SITES = {"defenseworld.net", "etfdailynews.com", "marketbeat.com", "americanbankingnews.com", "tickerreport.com"}
SPAM_TITLE = re.compile(r"shares (bought|sold|acquired|purchased) by|(sells|buys|acquires) [\d,]+ shares|"
                        r"stake (in|raised|lowered|cut)|position in|shares (up|down) [\d.]+%", re.I)

SNAPSHOT = [
    ("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq"), ("^RUT", "Russell 2000"), ("^VIX", "VIX"),
    ("CLUSD", "WTI oil"), ("GCUSD", "Gold"), ("DX-Y.NYB", "Dollar index"), ("BTCUSD", "Bitcoin"),
]


def get(path: str, key: str, **params) -> list | dict:
    resp = requests.get(f"{FMP}/{path}", params={**params, "apikey": key}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def quotes(symbols: list[str], key: str) -> list[dict]:
    out = []
    for i in range(0, len(symbols), 200):
        out.extend(get(f"v3/quote/{','.join(symbols[i:i + 200])}", key))
    return out


def large_caps(key: str) -> dict[str, dict]:
    rows = get("v3/stock-screener", key, marketCapMoreThan=MIN_MARKET_CAP, isEtf="false", isFund="false",
               isActivelyTrading="true", country="US", exchange="NYSE,NASDAQ", limit=5000)
    return {r["symbol"]: r for r in rows}


def daily_vol(closes: list[float]) -> float | None:
    """Stdev of daily simple returns. `closes` is oldest → newest."""
    rets = [b / a - 1 for a, b in zip(closes, closes[1:]) if a]
    if len(rets) < 20:
        return None
    mean = sum(rets) / len(rets)
    return math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))


def history_vol(symbol: str, before: str, key: str) -> float | None:
    """60-day daily volatility from closes strictly before `before` (YYYY-MM-DD),
    so today's move doesn't inflate its own baseline."""
    try:
        data = get(f"v3/historical-price-full/{symbol}", key, timeseries=70)
    except Exception:
        return None
    hist = [h for h in data.get("historical", []) if h["date"] < before][:61]
    return daily_vol([h["close"] for h in reversed(hist)])


def useful_news(news: list[dict]) -> list[dict]:
    return [n for n in news if n.get("site") not in SPAM_SITES and not SPAM_TITLE.search(n.get("title", ""))]


def short_name(name: str) -> str:
    """'Kinder Morgan, Inc.' → 'Kinder Morgan'. Shared suffixes like 'Inc' would
    otherwise make aggregate's title-similarity dedup merge unrelated movers."""
    return re.sub(r"[,\s]+(Inc|Corp|Corporation|Company|Co|Ltd|Limited|plc|L\.?P|N\.?V|S\.?A|AG|SE|Holdings)\.?$",
                  "", name, flags=re.I).strip() or name


def pct(v: float) -> str:
    return f"{v:+.1f}%"


def snapshot(key: str) -> list[dict]:
    by_sym = {q["symbol"]: q for q in quotes([s for s, _ in SNAPSHOT], key)}
    parts = [f"{name} {pct(by_sym[s]['changesPercentage'])}" for s, name in SNAPSHOT if s in by_sym]

    today = datetime.now(timezone.utc).date()
    rates = get("v4/treasury", key, **{"from": (today - timedelta(days=10)).isoformat(), "to": today.isoformat()})
    if len(rates) >= 2:  # newest first
        for tenor, label in (("year2", "2Y"), ("year10", "10Y")):
            bp = round((rates[0][tenor] - rates[1][tenor]) * 100)
            parts.append(f"{label} {rates[0][tenor]:.2f}% ({bp:+d}bp)")

    sectors = sorted(get("v3/sectors-performance", key), key=lambda s: float(s["changesPercentage"].rstrip("%")))
    if sectors:
        lo, hi = sectors[0], sectors[-1]
        parts.append(f"best sector {hi['sector']} {pct(float(hi['changesPercentage'].rstrip('%')))}, "
                     f"worst {lo['sector']} {pct(float(lo['changesPercentage'].rstrip('%')))}")

    spx = by_sym.get("^GSPC", {})
    session = datetime.fromtimestamp(spx.get("timestamp", 0), timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    return [{
        "title": f"Market close {session}: " + ", ".join(parts[:3]),
        "summary": "; ".join(parts),
        "description": "; ".join(parts[3:]),  # shown verbatim, not rewritten by Claude
        "url": "https://finance.yahoo.com/quote/%5EGSPC/",
        "source": "FMP Market",
        "category": "finance",
        "engagement": 1.0,
        "fetched_at": now,
        "published_at": now,
    }]


def rank_movers(rows: list[dict], vols: dict[str, float], min_z: float) -> list[dict]:
    """Attach z = move / own daily vol and keep |z| ≥ min_z, largest first."""
    out = []
    for q in rows:
        vol = vols.get(q["symbol"])
        if not vol:
            continue
        z = q["changesPercentage"] / 100 / vol
        if abs(z) >= min_z:
            out.append({**q, "z": round(z, 2)})
    return sorted(out, key=lambda q: abs(q["z"]), reverse=True)


def movers(key: str, limit: int, min_z: float) -> list[dict]:
    universe = large_caps(key)
    rows = [q for q in fresh_quotes(quotes(list(universe), key))
            if q.get("changesPercentage") is not None
            and (q.get("avgVolume") or 0) * (q.get("price") or 0) >= MIN_DOLLAR_VOLUME]
    if not rows:
        return []
    session = datetime.fromtimestamp(max(q["timestamp"] for q in rows), timezone.utc).date().isoformat()
    # Volatility lookups cost one call each; a large cap needs ≥ 2% to clear z ≥ 2 unless it barely moves.
    candidates = sorted((q for q in rows if abs(q["changesPercentage"]) >= 2),
                        key=lambda q: abs(q["changesPercentage"]), reverse=True)[:300]
    print(f"    {len(rows)} large caps, {len(candidates)} moved ≥ 2%", file=sys.stderr)
    with ThreadPoolExecutor(8) as pool:
        vols = dict(zip((q["symbol"] for q in candidates),
                        pool.map(lambda q: history_vol(q["symbol"], session, key), candidates)))
    ranked = rank_movers(candidates, vols, min_z)[:limit]

    now = datetime.now(timezone.utc).isoformat()
    items = []
    for q in ranked:
        sym = q["symbol"]
        since = (date.fromisoformat(session) - timedelta(days=2)).isoformat()
        try:
            news = [n for n in useful_news(get("v3/stock_news", key, tickers=sym, limit=20))
                    if n["publishedDate"][:10] >= since][:2]
        except Exception:
            news = []
        why = " | ".join(n["title"] for n in news) or "No headline found for this move."
        name = short_name(universe.get(sym, {}).get("companyName") or q.get("name", sym))
        items.append({
            "title": f"{sym} ({name}) {pct(q['changesPercentage'])}",
            "summary": f"{universe.get(sym, {}).get('sector', '')}, market cap ${q['marketCap'] / 1e9:,.0f}B. "
                       f"Headlines: {why}",
            "url": news[0]["url"] if news else f"https://finance.yahoo.com/quote/{sym}/",
            "source": "FMP Movers",
            "category": "finance",
            "ticker": sym,
            "engagement": abs(q["z"]),
            "engagement_raw": q["z"],
            "engagement_label": "σ move",
            "fetched_at": now,
            "published_at": news[0]["publishedDate"] if news else now,
        })
    return items


def upcoming_session(now: datetime) -> date:
    """Today's session if it hasn't closed yet (4 PM ET), else the next weekday. Ignores exchange holidays."""
    et = now.astimezone(ZoneInfo("America/New_York"))
    d = et.date() if et.hour < 16 else et.date() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def calendar(key: str, limit: int) -> list[dict]:
    now_dt = datetime.now(timezone.utc)
    day = upcoming_session(now_dt).isoformat()
    same_day = day == now_dt.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    universe = large_caps(key)
    # same-day pre-market reports and already-released macro prints aren't "coming up" any more
    earnings = [e for e in get("v3/earning_calendar", key, **{"from": day, "to": day})
                if e["symbol"] in universe and not (same_day and e.get("time") == "bmo")]
    earnings.sort(key=lambda e: universe[e["symbol"]]["marketCap"], reverse=True)
    when = {"bmo": "pre-market", "amc": "after close"}
    er = [f"{e['symbol']} ({when.get(e.get('time'), 'time n/a')}"
          + (f", EPS est {e['epsEstimated']:.2f}" if e.get("epsEstimated") is not None else "") + ")"
          for e in earnings[:limit]]

    macro = [m for m in get("v3/economic_calendar", key, **{"from": day, "to": day})
             if m.get("country") == "US" and m.get("impact") == "High"
             and m["date"] > now_dt.strftime("%Y-%m-%d %H:%M:%S")]
    mc = [f"{m['event']} {m['date'][11:16]} UTC" + (f" (est {m['estimate']})" if m.get("estimate") is not None else "")
          for m in sorted(macro, key=lambda m: m["date"])]

    if not er and not mc:
        return []
    parts = []
    if er:
        parts.append(f"Earnings ({len(earnings)} large caps): " + ", ".join(er))
    if mc:
        parts.append("US macro: " + "; ".join(mc))
    now = datetime.now(timezone.utc).isoformat()
    return [{
        "title": f"Coming up {day}: " + (", ".join(e["symbol"] for e in earnings[:5]) or mc[0]),
        "summary": " — ".join(parts),
        "description": " — ".join(parts),  # shown verbatim, not rewritten by Claude
        "url": "https://financialmodelingprep.com/economic-calendar",
        "source": "FMP Calendar",
        "category": "finance",
        "engagement": 1.0,
        "fetched_at": now,
        "published_at": now,
    }]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["snapshot", "movers", "calendar"], required=True)
    parser.add_argument("--limit", type=int, default=8, help="Movers to return / earnings to list (default: 8)")
    parser.add_argument("--min-z", type=float, default=2.0, help="Min |move| in own daily-vol units (default: 2)")
    args = parser.parse_args()

    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        print("  ERROR: FMP_API_KEY not set", file=sys.stderr)
        print("[]")
        return

    print(f"  Fetching FMP market {args.part}...", file=sys.stderr)
    if args.part == "snapshot":
        items = snapshot(key)
    elif args.part == "movers":
        items = movers(key, args.limit, args.min_z)
    else:
        items = calendar(key, args.limit)
    print(f"    {len(items)} items", file=sys.stderr)
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
