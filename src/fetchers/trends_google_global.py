#!/usr/bin/env python3
"""
Google Trends global fetcher — fetches trending searches across all ~125 countries
using a single playwright session for tokens, then parallel HTTP requests per country.
Aggregates by cross-country appearance count to surface genuinely global trends.

Usage:
  python fetchers/trends_google_global.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser
import requests
from playwright.sync_api import sync_playwright

from stats import score_items

NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# Single/double-char queries are search-bar noise, not real trends
NOISE_RE = re.compile(r"^.{1,2}$")

COUNTRIES = [
    ("AL", "Albania"), ("DZ", "Algeria"), ("AO", "Angola"), ("AR", "Argentina"),
    ("AM", "Armenia"), ("AU", "Australia"), ("AT", "Austria"), ("AZ", "Azerbaijan"),
    ("BH", "Bahrain"), ("BD", "Bangladesh"), ("BY", "Belarus"), ("BE", "Belgium"),
    ("BJ", "Benin"), ("BO", "Bolivia"), ("BA", "Bosnia & Herzegovina"), ("BR", "Brazil"),
    ("BG", "Bulgaria"), ("BF", "Burkina Faso"), ("KH", "Cambodia"), ("CM", "Cameroon"),
    ("CA", "Canada"), ("CL", "Chile"), ("CO", "Colombia"), ("CD", "Congo - Kinshasa"),
    ("CR", "Costa Rica"), ("CI", "Côte d'Ivoire"), ("HR", "Croatia"), ("CU", "Cuba"),
    ("CY", "Cyprus"), ("CZ", "Czechia"), ("DK", "Denmark"), ("DO", "Dominican Republic"),
    ("EC", "Ecuador"), ("EG", "Egypt"), ("SV", "El Salvador"), ("EE", "Estonia"),
    ("ET", "Ethiopia"), ("FI", "Finland"), ("FR", "France"), ("GE", "Georgia"),
    ("DE", "Germany"), ("GH", "Ghana"), ("GR", "Greece"), ("GT", "Guatemala"),
    ("HT", "Haiti"), ("HN", "Honduras"), ("HK", "Hong Kong"), ("HU", "Hungary"),
    ("IN", "India"), ("ID", "Indonesia"), ("IR", "Iran"), ("IQ", "Iraq"),
    ("IE", "Ireland"), ("IL", "Israel"), ("IT", "Italy"), ("JM", "Jamaica"),
    ("JP", "Japan"), ("JO", "Jordan"), ("KZ", "Kazakhstan"), ("KE", "Kenya"),
    ("KW", "Kuwait"), ("KG", "Kyrgyzstan"), ("LV", "Latvia"), ("LB", "Lebanon"),
    ("LY", "Libya"), ("LT", "Lithuania"), ("MY", "Malaysia"), ("ML", "Mali"),
    ("MX", "Mexico"), ("MD", "Moldova"), ("MA", "Morocco"), ("MZ", "Mozambique"),
    ("MM", "Myanmar (Burma)"), ("NP", "Nepal"), ("NL", "Netherlands"), ("NZ", "New Zealand"),
    ("NI", "Nicaragua"), ("NG", "Nigeria"), ("MK", "North Macedonia"), ("NO", "Norway"),
    ("OM", "Oman"), ("PK", "Pakistan"), ("PS", "Palestine"), ("PA", "Panama"),
    ("PY", "Paraguay"), ("PE", "Peru"), ("PH", "Philippines"), ("PL", "Poland"),
    ("PT", "Portugal"), ("PR", "Puerto Rico"), ("QA", "Qatar"), ("RO", "Romania"),
    ("RU", "Russia"), ("SA", "Saudi Arabia"), ("SN", "Senegal"), ("RS", "Serbia"),
    ("SG", "Singapore"), ("SK", "Slovakia"), ("SI", "Slovenia"), ("ZA", "South Africa"),
    ("KR", "South Korea"), ("ES", "Spain"), ("LK", "Sri Lanka"), ("SE", "Sweden"),
    ("CH", "Switzerland"), ("SY", "Syria"), ("TW", "Taiwan"), ("TZ", "Tanzania"),
    ("TH", "Thailand"), ("TT", "Trinidad & Tobago"), ("TN", "Tunisia"), ("TR", "Türkiye"),
    ("TM", "Turkmenistan"), ("UG", "Uganda"), ("UA", "Ukraine"), ("AE", "United Arab Emirates"),
    ("GB", "United Kingdom"), ("US", "United States"), ("UY", "Uruguay"), ("UZ", "Uzbekistan"),
    ("VE", "Venezuela"), ("VN", "Vietnam"), ("YE", "Yemen"), ("ZM", "Zambia"), ("ZW", "Zimbabwe"),
]


def get_session_tokens() -> dict:
    """Load the trends page once to capture f.sid, bl, and cookies."""
    captured = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_request(req):
            if "batchexecute" in req.url and "i0OFE" in req.url and "url" not in captured:
                captured["url"] = req.url

        page.on("request", on_request)
        page.goto("https://trends.google.com/trending?geo=US&hl=en-US",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(12000)
        captured["cookies"] = {c["name"]: c["value"] for c in context.cookies()}
        browser.close()
    return captured


def fetch_country(code: str, fsid: str, bl: str, cookies: dict) -> list[dict]:
    endpoint = (
        "https://trends.google.com/_/TrendsUi/data/batchexecute"
        f"?rpcids=i0OFE&source-path=%2Ftrending&f.sid={fsid}&bl={bl}&hl=en-US&rt=c"
    )
    inner = json.dumps([None, None, code, 0, "en-US", 24, 1])
    freq = json.dumps([[["i0OFE", inner, None, "generic"]]])
    body = urllib.parse.urlencode({"f.req": freq})
    headers = {
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        "referer": "https://trends.google.com/",
        "x-same-domain": "1",
        "user-agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    r = requests.post(endpoint, data=body, headers=headers, cookies=cookies, timeout=15)
    lines = r.text.splitlines()
    json_line = next((l for l in lines if l.startswith("[[")), "")
    if not json_line:
        return []
    outer = json.loads(json_line)
    inner_data = json.loads(outer[0][2])
    trends = inner_data[1] or []
    items = []
    for t in trends[:20]:
        query = t[0]
        traffic = float(t[6]) if len(t) > 6 and t[6] else 0.0
        items.append({"title": query, "traffic": traffic})
    return items


def fetch_headline(query: str) -> tuple[str, str]:
    try:
        url = NEWS_RSS.format(query=urllib.parse.quote(query))
        feed = feedparser.parse(url)
        if feed.entries:
            e = feed.entries[0]
            return e.title, e.get("link", "")
    except Exception:
        pass
    return "", ""


def fetch_global(limit: int) -> list[dict]:
    print("  Getting session tokens...", file=sys.stderr)
    session = get_session_tokens()
    base_url = session.get("url", "")
    if not base_url:
        print("  ERROR: could not capture session tokens", file=sys.stderr)
        return []
    fsid = re.search(r"f\.sid=([^&]+)", base_url).group(1)
    bl = re.search(r"bl=([^&]+)", base_url).group(1)
    cookies = session["cookies"]

    aggregated: dict[str, dict] = defaultdict(
        lambda: {"title": "", "countries": [], "total_volume": 0.0}
    )

    def fetch_one(code, name):
        try:
            items = fetch_country(code, fsid, bl, cookies)
            print(f"  {name} ({code}): {len(items)} items", file=sys.stderr, flush=True)
            return name, items
        except Exception as e:
            print(f"  {name} ({code}): ERROR {e}", file=sys.stderr, flush=True)
            return name, []

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(fetch_one, code, name): (code, name) for code, name in COUNTRIES}
        for future in as_completed(futures):
            _, items = future.result()
            country_name = futures[future][1]
            for item in items:
                key = item["title"].lower().strip()
                if NOISE_RE.match(key):
                    continue
                if not aggregated[key]["title"]:
                    aggregated[key]["title"] = item["title"]
                aggregated[key]["countries"].append(country_name)
                aggregated[key]["total_volume"] += item["traffic"]

    ranked = sorted(
        aggregated.values(),
        key=lambda x: (len(x["countries"]), x["total_volume"]),
        reverse=True,
    )

    now = datetime.now(timezone.utc).isoformat()
    top = ranked[:limit]

    # Fetch headlines in parallel
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_headline, r["title"]): i for i, r in enumerate(top)}
        for future in as_completed(futures):
            idx = futures[future]
            headline, article_url = future.result()
            top[idx]["summary"] = headline
            top[idx]["article_url"] = article_url

    items_out = []
    for r in top:
        country_count = len(r["countries"])
        url = r.get("article_url") or (
            f"https://trends.google.com/trending?geo=&q={urllib.parse.quote(r['title'])}"
        )
        items_out.append({
            "title": r["title"],
            "summary": r.get("summary", ""),
            "url": url,
            "source": "Google Trends Global",
            "category": "news",
            "country_count": country_count,
            "countries": r["countries"],
            "total_volume": r["total_volume"],
            "fetched_at": now,
            "published_at": None,
        })

    return items_out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Max global trends to return (default: 20)")
    args = parser.parse_args()

    items = fetch_global(args.limit)
    print(f"  Google Trends Global: {len(items)} items", file=sys.stderr)
    items = score_items(items, "Google Trends Global", "country_count")
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
