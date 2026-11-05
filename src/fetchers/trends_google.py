#!/usr/bin/env python3
"""
Google Trends fetcher — pulls the past-24h "Trending now" list by loading
trends.google.com/trending in headless Chromium and taking its CSV export, sorted
by search volume. The page's batchexecute endpoint rejects direct requests with
error [7] since 2026-11-05. The public RSS feed only lists the ~10 most recently
started trends, so it misses the big ones; it's used here just for news headlines.

Usage:
  python fetchers/trends_google.py [--geo GEO] [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import asyncio
import csv
import io
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.async_api import async_playwright

from stats import score_items

HT_NS = "https://trends.google.com/trending/rss"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


PAGE_TIMEOUT_MS = 45_000
GEO_TIMEOUT_S = 60  # Caps the several PAGE_TIMEOUT_MS steps of one geo
RUN_TIMEOUT_S = 15 * 60  # aggregate.py waits on fetchers with no timeout of its own
CONCURRENCY = 2  # Chromium tabs at once; timed 4.1s/geo vs 6.7s/geo with 4 on this 2-core host


def fetch_headlines(geo: str) -> dict[str, tuple[str, str]]:
    """Query -> (headline, article_url) from the RSS feed.

    The RSS feed only carries the ~10 most recently started trends, so it
    only covers a few of the high-volume ones; it is used for headlines only.
    """
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        r = requests.get(url, headers={"user-agent": USER_AGENT}, timeout=20)
        root = ET.fromstring(r.text)
    except Exception as e:
        print(f"  WARN: RSS headlines for {geo} failed: {e}", file=sys.stderr)
        return {}
    out = {}
    for item in root.findall(".//item"):
        news = item.find(f"{{{HT_NS}}}news_item")
        if news is None:
            continue
        query = (item.findtext("title") or "").strip().lower()
        out[query] = (
            (news.findtext(f"{{{HT_NS}}}news_item_title") or "").strip(),
            (news.findtext(f"{{{HT_NS}}}news_item_url") or "").strip(),
        )
    return out


def parse_traffic(text: str | None) -> float:
    """Turn '2,000+' / '20K+' / '1M+' into a float."""
    if not text:
        return 0.0
    s = text.strip().replace(",", "").replace("+", "").upper()
    m = re.match(r"^([\d.]+)\s*([KM]?)$", s)
    if not m:
        return 0.0
    return float(m.group(1)) * {"K": 1_000, "M": 1_000_000}.get(m.group(2), 1)


def parse_started(text: str | None) -> datetime | None:
    try:
        return datetime.strptime((text or "").strip(), "%B %d, %Y at %I:%M:%S %p UTC").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_export(text: str) -> list[dict]:
    """Rows of the page's CSV export by descending volume, as query / started / volume / related."""
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        query = (row["Trends"] or "").strip()
        if not query:
            continue
        rows.append({
            "query": query,
            "started": parse_started(row["Started"]),
            "volume": parse_traffic(row["Search volume"]),
            "related": [q.strip() for q in (row["Trend breakdown"] or "").split(",") if q.strip()],
        })
    rows.sort(key=lambda r: r["volume"], reverse=True)
    return rows


async def skip_heavy_assets(route):
    if route.request.resource_type in ("image", "font", "media"):
        await route.abort()
    else:
        await route.continue_()


async def export_csv(context, geo: str, hours: int) -> str:
    page = await context.new_page()
    try:
        page.set_default_timeout(PAGE_TIMEOUT_MS)
        await page.goto(f"https://trends.google.com/trending?geo={geo}&hours={hours}", wait_until="domcontentloaded")
        await page.locator("table tbody tr td:visible").first.wait_for()
        await page.get_by_text("Export").first.click()
        async with page.expect_download() as download_info:
            await page.locator("[role=menuitem]", has_text="CSV").first.click()
        download = await download_info.value
        return Path(await download.path()).read_text(encoding="utf-8-sig")
    finally:
        await page.close()


async def fetch_trending_async(geos: list[str], hours: int) -> dict[str, list[dict]]:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    results = {}

    async def fetch_one(context, geo):
        async with semaphore:
            try:
                text = await asyncio.wait_for(export_csv(context, geo, hours), GEO_TIMEOUT_S)
                results[geo] = parse_export(text)
            except Exception as e:
                reason = (str(e) or repr(e)).splitlines()[0]
                print(f"  ERROR: {geo} trends export failed: {reason}", file=sys.stderr, flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(locale="en-US", timezone_id="UTC", accept_downloads=True)
            await context.route("**/*", skip_heavy_assets)
            tasks = [asyncio.create_task(fetch_one(context, geo)) for geo in geos]
            _, pending = await asyncio.wait(tasks, timeout=RUN_TIMEOUT_S)
            for task in pending:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if pending:
                print(f"  ERROR: trends run deadline hit, {len(pending)} geos skipped", file=sys.stderr, flush=True)
        finally:
            await browser.close()
    return results


def fetch_trending(geos: list[str], hours: int = 24) -> dict[str, list[dict]]:
    """Geo -> trend rows for the past `hours`, as shown on the web UI. Failed geos are left out."""
    return asyncio.run(fetch_trending_async(geos, hours))


def fetch(geo: str, limit: int) -> list[dict]:
    rows = fetch_trending([geo]).get(geo, [])
    headlines = fetch_headlines(geo)

    now = datetime.now(timezone.utc).isoformat()
    items = []
    for row in rows[:limit]:
        query = row["query"]
        published = row["started"].isoformat() if row["started"] else None
        headline, article_url = headlines.get(query.lower(), ("", ""))
        if not headline:
            related = [q for q in row["related"] if q.lower() != query.lower()]
            headline = ", ".join(related[:5])
        link = article_url or f"https://trends.google.com/trending?geo={geo}&q={urllib.parse.quote(query)}"

        items.append({
            "title": query,
            "summary": headline,
            "url": link,
            "source": "Google Trends",
            "category": "news",
            "traffic": row["volume"],
            "fetched_at": now,
            "published_at": published,
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--geo", default="US", help="Country code (default: US)")
    parser.add_argument("--limit", type=int, default=20, help="Max trends to fetch (default: 20)")
    args = parser.parse_args()

    items = fetch(args.geo, args.limit)
    print(f"  Google Trends ({args.geo}): {len(items)} items", file=sys.stderr)
    items = score_items(items, "Google Trends", "traffic", "searches")
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
