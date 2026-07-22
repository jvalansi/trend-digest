#!/usr/bin/env python3
"""
Google Trends global fetcher — pulls trending searches across ~125 countries
from the official public per-country RSS feed at
trends.google.com/trending/rss?geo=XX. Aggregates by cross-country appearance
count to surface genuinely global trends.

Usage:
  python fetchers/trends_google_global.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser
import requests
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException

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


HT_NS = "https://trends.google.com/trending/rss"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def parse_traffic(text: str | None) -> float:
    if not text:
        return 0.0
    s = text.strip().replace(",", "").replace("+", "").upper()
    m = re.match(r"^([\d.]+)\s*([KM]?)$", s)
    if not m:
        return 0.0
    n = float(m.group(1))
    mult = {"K": 1_000, "M": 1_000_000}.get(m.group(2), 1)
    return n * mult


def fetch_country(code: str) -> list[dict]:
    url = f"https://trends.google.com/trending/rss?geo={code}"
    try:
        r = requests.get(url, headers={"user-agent": USER_AGENT}, timeout=15)
    except Exception:
        return []
    if r.status_code != 200 or not r.text.strip().startswith("<?xml"):
        return []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []
    items = []
    for item in root.findall(".//item"):
        query = (item.findtext("title") or "").strip()
        if not query:
            continue
        traffic = parse_traffic(item.findtext(f"{{{HT_NS}}}approx_traffic"))
        news = item.find(f"{{{HT_NS}}}news_item")
        headline = (news.findtext(f"{{{HT_NS}}}news_item_title") or "").strip() if news is not None else ""
        article_url = (news.findtext(f"{{{HT_NS}}}news_item_url") or "").strip() if news is not None else ""
        items.append({
            "title": query,
            "traffic": traffic,
            "headline": headline,
            "article_url": article_url,
        })
    return items


def translate_to_english(title: str) -> str:
    """Return the English translation of title, or the original if already English or on error."""
    try:
        if detect(title) == "en":
            return title
    except LangDetectException:
        return title
    try:
        return GoogleTranslator(source="auto", target="en").translate(title) or title
    except Exception:
        return title


def batch_translate(titles: list[str]) -> dict[str, str]:
    """Return mapping original_title → english_title for all titles."""
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(translate_to_english, t): t for t in titles}
        return {futures[f]: f.result() for f in as_completed(futures)}


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
    raw_results: list[tuple[str, list[dict]]] = []

    def fetch_one(code, name):
        try:
            items = fetch_country(code)
            print(f"  {name} ({code}): {len(items)} items", file=sys.stderr, flush=True)
            return name, items
        except Exception as e:
            print(f"  {name} ({code}): ERROR {e}", file=sys.stderr, flush=True)
            return name, []

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_one, code, name): (code, name) for code, name in COUNTRIES}
        for future in as_completed(futures):
            country_name, items = future.result()
            raw_results.append((country_name, items))

    # Collect all unique titles and translate to English for deduplication
    all_titles = {item["title"] for _, items in raw_results for item in items}
    print(f"  Translating {len(all_titles)} unique titles to English...", file=sys.stderr)
    translation_map = batch_translate(list(all_titles))

    aggregated: dict[str, dict] = defaultdict(
        lambda: {"title": "", "countries": [], "total_volume": 0.0}
    )
    for country_name, items in raw_results:
        for item in items:
            en_title = translation_map.get(item["title"], item["title"])
            key = en_title.lower().strip()
            if NOISE_RE.match(key):
                continue
            if not aggregated[key]["title"]:
                aggregated[key]["title"] = en_title
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
    items = score_items(items, "Google Trends Global", "country_count", "countries")
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
