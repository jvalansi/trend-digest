#!/usr/bin/env python3
"""
GitHub fetcher — pulls trending repositories and releases.

Usage:
  python fetchers/github.py [--mode trending|releases] [--language LANG] [--since daily|weekly|monthly] [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from stats import score_items

TRENDING_URL = "https://github.com/trending"
GH_API = "https://api.github.com"


def fetch_trending(language: str, since: str, limit: int) -> list[dict]:
    url = TRENDING_URL
    params = []
    if language:
        params.append(f"l={urllib.parse.quote(language)}")
    if since:
        params.append(f"since={since}")
    if params:
        url += "?" + "&".join(params)

    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode()

    results = []
    # Parse repo blocks from trending page
    for block in re.findall(r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>', html, re.DOTALL)[:limit]:
        name_match = re.search(r'href="/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"', block)
        desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>\s*(.*?)\s*</p>', block, re.DOTALL)
        stars_match = re.search(r'octicon-star.*?</svg>\s*([\d,]+)', block, re.DOTALL)
        today_match = re.search(r'([\d,]+)\s*stars? today', block)
        lang_match = re.search(r'itemprop="programmingLanguage"[^>]*>(.*?)<', block)

        if not name_match:
            continue

        repo = name_match.group(1)
        # Skip sponsor blocks
        if repo.startswith("sponsors/"):
            continue

        desc = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip() if desc_match else ""
        stars = stars_match.group(1).replace(",", "") if stars_match else None
        stars_today = today_match.group(1).replace(",", "") if today_match else None
        lang = lang_match.group(1).strip() if lang_match else None

        results.append({
            "title": repo,
            "summary": desc,
            "url": f"https://github.com/{repo}",
            "source": "GitHub Trending",
            "category": "tech",
            "stars": int(stars) if stars else None,
            "stars_today": int(stars_today) if stars_today else None,
            "language": lang,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        })

    return results


def fetch_releases(language: str, limit: int) -> list[dict]:
    # Search for recently released repos with many stars
    query = f"stars:>500+is:public"
    if language:
        query += f"+language:{language}"
    url = f"{GH_API}/search/repositories?q={urllib.parse.quote(query)}&sort=updated&order=desc&per_page={min(limit, 30)}"
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())

    results = []
    for repo in data.get("items", []):
        results.append({
            "title": repo["full_name"],
            "summary": repo.get("description") or "",
            "url": repo["html_url"],
            "source": "GitHub",
            "category": "tech",
            "stars": repo.get("stargazers_count"),
            "language": repo.get("language"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": repo.get("updated_at"),
        })
    return results


def main():
    import urllib.parse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="trending", choices=["trending", "releases"])
    parser.add_argument("--language", default="", help="Filter by programming language")
    parser.add_argument("--since", default="daily", choices=["daily", "weekly", "monthly"], help="Trending period (default: daily)")
    parser.add_argument("--limit", type=int, default=25, help="Max items to fetch (default: 25)")
    args = parser.parse_args()

    if args.mode == "trending":
        print(f"  Fetching GitHub trending ({args.since})...", file=sys.stderr)
        results = fetch_trending(args.language, args.since, args.limit)
    else:
        print(f"  Fetching recently updated popular repos...", file=sys.stderr)
        results = fetch_releases(args.language, args.limit)

    # Use stars_today as engagement signal (velocity), fall back to total stars
    for item in results:
        item["score"] = item.pop("stars_today") or item.pop("stars") or 0
    results = score_items(results, "GitHub Trending", "score")

    print(f"  Got {len(results)} repos", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
