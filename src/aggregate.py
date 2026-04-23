#!/usr/bin/env python3
"""
Aggregator — runs all fetchers, merges output, scores, and ranks.

Output format:
  {
    "rss": [...],           # merged/deduped RSS stories, scored by cross-source × authority × recency
    "sections": {           # per-source top N, ranked by native metric
      "Hacker News": [...],
      "GitHub (daily)": [...],
      ...
    }
  }

Usage:
  python aggregate.py [--limit N] [--section-limit N] [--output FILE] [--mode tech|news]
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

try:
    from deep_translator import GoogleTranslator
    from langdetect import detect, LangDetectException
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False

PYTHON = sys.executable

SOURCE_AUTHORITY = {
    "The Verge":       1.0,
    "TechCrunch":      1.0,
    "Ars Technica":    1.1,
    "Wired":           0.9,
    "MIT Tech Review": 1.2,
    "VentureBeat":     0.8,
    "Engadget":        0.8,
    "ZDNet":           0.7,
    "Hacker News":     1.3,
    "GitHub Trending (daily)":  0.7,
    "GitHub Trending (weekly)": 0.6,
    "X (via Grok)":    0.9,
    "YouTube Trending": 1.0,
    "Yahoo Japan":     1.1,
    "Yahoo News":      1.0,
    "Globo":           0.9,
    "New York Times":  1.2,
    "BBC News":        1.2,
    "CNN":             1.1,
    "MSN News":        0.8,
    "QQ News":         0.9,
    "The Guardian":    1.1,
    "Times of India":  0.9,
    "Google News":     1.0,
    "Fox News":        1.0,
    "UOL":             0.8,
    "Infobae":         0.8,
    "Naver News":      0.9,
    "Google Trends":      1.1,
    "Wikipedia Trending": 1.0,
    "Reddit":             1.1,
    "Bilibili Trending":  0.9,
}
DEFAULT_AUTHORITY = 0.8

# is_rss=True items are merged/deduped together.
# Others get their own section with top section_limit items.
FETCHERS = {
    "tech": [
        {"cmd": ["python", "src/fetchers/rss.py", "--limit", "20", "--category", "tech"], "is_rss": True},
        {"cmd": ["python", "src/fetchers/hn.py", "--feed", "top", "--limit", "30"], "section": "Hacker News"},
        {"cmd": ["python", "src/fetchers/youtube.py", "--limit", "20", "--category", "tech"], "section": "YouTube Tech"},
        {"cmd": ["python", "src/fetchers/github.py", "--limit", "25"], "section": "GitHub Trending"},
        {"cmd": ["python", "src/fetchers/github.py", "--limit", "25", "--since", "weekly"], "section": "GitHub Trending"},
        {"cmd": ["python", "src/fetchers/x.py", "--limit", "10", "--category", "tech"], "section": "X Tech"},
        {"cmd": ["python", "src/fetchers/trends_reddit.py", "--limit", "25", "--mode", "tech"], "section": "Reddit Tech"},
    ],
    "news": [
        {"cmd": ["python", "src/fetchers/rss.py", "--limit", "20", "--category", "news"], "is_rss": True},
        {"cmd": ["python", "src/fetchers/trends_google.py", "--limit", "20"], "section": "Google Trends"},
        {"cmd": ["python", "src/fetchers/trends_wikipedia.py", "--limit", "20"], "section": "Wikipedia Trending"},
        {"cmd": ["python", "src/fetchers/trends_reddit.py", "--limit", "25", "--mode", "news"], "section": "Reddit News"},
        {"cmd": ["python", "src/fetchers/trends_bilibili.py", "--limit", "20"], "section": "Bilibili Trending"},
        {"cmd": ["python", "src/fetchers/x.py", "--limit", "10", "--category", "news"], "section": "X News"},
        {"cmd": ["python", "src/fetchers/youtube.py", "--limit", "20", "--category", "news"], "section": "YouTube News"},
    ],
}


def run_fetcher(cmd: list[str]) -> list[dict]:
    result = subprocess.run(
        [PYTHON if c == "python" else c for c in cmd],
        capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), "..")
    )
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            print(f"  {line}", file=sys.stderr)
    if result.returncode != 0:
        print(f"  ERROR running {cmd[1]}: {result.stderr[-200:]}", file=sys.stderr)
        return []
    return json.loads(result.stdout)


def translate_to_english(text: str) -> str:
    if not TRANSLATION_AVAILABLE or not text:
        return text
    try:
        if detect(text) == "en":
            return text
        return GoogleTranslator(source="auto", target="en").translate(text) or text
    except Exception:
        return text


def title_words(title: str) -> set[str]:
    stopwords = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "was", "were",
                 "has", "have", "been", "will", "would", "could", "should", "that", "this", "with", "from", "by",
                 "as", "its", "it", "be", "after", "says", "say", "over", "new", "amid", "than"}
    entities = {w.lower() for w in re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', title) if w.lower() not in stopwords}
    return entities if entities else {w for w in title.lower().split() if w not in stopwords and len(w) > 2}


def similarity(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def recency_score(published_at: str | None) -> float:
    if not published_at:
        return 0.5
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        return math.exp(-age_hours * math.log(2) / 12)
    except Exception:
        return 0.5


def merge_rss(items: list[dict]) -> list[dict]:
    """
    Merge/dedup RSS items. Score = cross_source_count × authority × recency.
    No z-score — cross-source mention count is the engagement signal for RSS.
    """
    groups: list[list[dict]] = []
    group_words: list[set] = []

    for item in items:
        title_en = translate_to_english(item["title"])
        if title_en != item["title"]:
            item["title_en"] = title_en
        words = title_words(title_en)
        matched = None
        for i, gw in enumerate(group_words):
            if similarity(words, gw) > 0.25:
                matched = i
                break
        if matched is not None:
            groups[matched].append(item)
            group_words[matched] |= words
        else:
            groups.append([item])
            group_words.append(words)

    results = []
    for group in groups:
        canonical = max(group, key=lambda x: len(x.get("summary", "")))
        canonical = dict(canonical)

        sources = list({i["source"] for i in group})
        canonical["sources"] = sources
        canonical["mention_count"] = len(group)

        cross_bonus = math.log1p(len(sources) - 1)
        authority = max(SOURCE_AUTHORITY.get(s, DEFAULT_AUTHORITY) for s in sources)
        recency = recency_score(canonical.get("published_at"))

        canonical["score"] = round((1 + cross_bonus) * authority * recency, 4)
        results.append(canonical)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="Top N RSS items (default: 5)")
    parser.add_argument("--section-limit", type=int, default=5, help="Top N per non-RSS section (default: 5)")
    parser.add_argument("--output", help="Write output to FILE instead of stdout")
    parser.add_argument("--mode", default="tech", choices=["tech", "news"], help="Digest mode (default: tech)")
    args = parser.parse_args()

    fetchers = FETCHERS[args.mode]
    rss_items = []
    sections = {}

    section_pools: dict[str, list[dict]] = {}

    for fetcher in fetchers:
        cmd = fetcher["cmd"]
        print(f"\n[{cmd[1]}]", file=sys.stderr)
        items = run_fetcher(cmd)

        if fetcher.get("is_rss"):
            rss_items.extend(items)
            print(f"  RSS subtotal: {len(rss_items)} items", file=sys.stderr)
        else:
            section = fetcher["section"]
            section_pools.setdefault(section, []).extend(items)
            print(f"  {section}: +{len(items)} items", file=sys.stderr)

    for section, pool in section_pools.items():
        # Dedup by URL, preserving order (highest-engagement first from each fetcher)
        seen_urls = set()
        unique = []
        for item in pool:
            url = item.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique.append(item)
        top = unique[:args.section_limit]
        if top:
            sections[section] = top
        print(f"  {section}: {len(top)} unique items (from {len(pool)} pooled)", file=sys.stderr)

    print(f"\nRSS raw: {len(rss_items)} items", file=sys.stderr)
    rss_merged = merge_rss(rss_items)
    rss_ranked = sorted(rss_merged, key=lambda x: x["score"], reverse=True)
    rss_top = rss_ranked[:args.limit]
    print(f"RSS after merge: {len(rss_merged)} unique → top {len(rss_top)}", file=sys.stderr)

    output_data = {"rss": rss_top, "sections": sections}
    output = json.dumps(output_data, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\nWrote to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
