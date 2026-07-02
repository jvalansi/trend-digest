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

from translate import translate_items, translate_to_english

PYTHON = sys.executable

# Weights are popularity-based proxies for "what's trending in the world":
# Similarweb monthly-visit tiers map roughly to >20M→1.3, 5-20M→1.1, 1-5M→0.9, else→0.8.
# Sources with unverified traffic are left at prior values and noted below.
SOURCE_AUTHORITY = {
    # Tech RSS
    "The Verge":       1.1,   # ~12.6M visits
    "TechCrunch":      1.1,   # ~14M
    "Ars Technica":    1.1,   # ~10.6M
    "Wired":           1.3,   # ~20M
    "MIT Tech Review": 0.9,   # ~1.3M
    "VentureBeat":     0.9,   # ~1.4M
    "Engadget":        1.1,   # ~6.5M
    "ZDNet":           0.9,   # ~1.9M
    # News RSS (Similarweb global news ranks, docs/sources/news.md)
    "Yahoo Japan":     1.3,   # #1
    "Globo":           1.3,   # #3
    "New York Times":  1.3,   # #5
    "BBC News":        1.1,   # #6
    "CNN":             1.1,   # #8
    "The Guardian":    1.1,   # #11
    "Times of India":  1.1,   # #12
    "Google News":     1.1,   # #14
    "Fox News":        1.1,   # #15
    "UOL":             0.9,   # #16
    "Infobae":         0.9,   # #17
    # Finance RSS
    "Yahoo Finance":   1.3,   # top-10 news publisher
    "investing.com":   1.3,   # ~161M
    "MarketWatch":     1.0,   # mid-tier, declining
    "Reuters Business":1.3,   # reuters.com ~24M (business subsection)
    # Science RSS
    "Nature":             1.3,   # ~35M
    "Science":            1.1,   # ~7M
    "New Scientist":      0.9,   # ~4.8M
    "Scientific American":0.9,   # ~4.8M
    "Ars Technica Science":1.1,  # parity with Ars main
    "bioRxiv":            0.9,   # ~2.4M
    # Sections (used when section items leak into the RSS path; sections normally
    # use per-fetcher engagement z-scores, not authority)
    "Hacker News":     1.3,
    "GitHub Trending (daily)":  0.7,
    "GitHub Trending (weekly)": 0.6,
    "X (via Grok)":    0.9,
    "HF Papers":       1.2,
    "HF Models":       1.0,
    "YouTube Trending": 1.0,
    "Google Trends":        1.1,
    "Google Trends Global": 1.3,
    "Wikipedia Trending": 1.0,
    "Reddit":             1.1,
    "Bilibili Trending":  0.9,
    "ETF Volume":         1.3,
    "Polymarket":         1.2,
    "OpenAlex Early Signal": 1.3,
    "arXiv n-gram Burst": 1.3,
    "Semantic Scholar":   1.0,
    "Altmetric":          1.3,
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
        {"cmd": ["python", "src/fetchers/hf_papers.py", "--limit", "20"], "section": "HF Papers"},
        {"cmd": ["python", "src/fetchers/hf_models.py", "--limit", "15"], "section": "HF Models"},
    ],
    "science": [
        {"cmd": ["python", "src/fetchers/rss.py", "--limit", "20", "--category", "science"], "is_rss": True},
        {"cmd": ["python", "src/fetchers/altmetric.py", "--limit", "20"], "section": "Altmetric"},
        {"cmd": ["python", "src/fetchers/semantic_scholar.py", "--limit", "20", "--mode", "science"], "section": "Semantic Scholar"},
        {"cmd": ["python", "src/fetchers/trends_reddit.py", "--limit", "25", "--mode", "science"], "section": "Reddit Science"},
        {"cmd": ["python", "src/fetchers/openalex_early_signal.py"], "section": "OpenAlex Early Signal", "section_limit": 5},
        {"cmd": ["python", "src/fetchers/arxiv_ngram_burst.py"], "section": "arXiv n-gram Burst", "section_limit": 8},
    ],
    "finance": [
        {"cmd": ["python", "src/fetchers/rss.py", "--limit", "20", "--category", "finance"], "is_rss": True},
        {"cmd": ["python", "src/fetchers/trends_reddit.py", "--limit", "25", "--mode", "finance"], "section": "Reddit Finance"},
        {"cmd": ["python", "src/fetchers/x.py", "--limit", "10", "--category", "finance"], "section": "X Finance"},
        {"cmd": ["python", "src/fetchers/etf_volume.py", "--limit", "5", "--min-ratio", "0"], "section": "ETF Volume Anomalies"},
        {"cmd": ["python", "src/fetchers/polymarket.py", "--limit", "10"], "section": "Polymarket"},
    ],
    "news": [
        {"cmd": ["python", "src/fetchers/rss.py", "--limit", "20", "--category", "news"], "is_rss": True},
        {"cmd": ["python", "src/fetchers/trends_google.py", "--limit", "20"], "section": "Google Trends", "section_limit": 10},
        {"cmd": ["python", "src/fetchers/trends_google_global.py", "--limit", "20"], "section": "Google Trends Global", "section_limit": 10},
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


def _group_by_title(items: list[dict]) -> list[list[dict]]:
    """Group items whose title-word sets overlap (>0.25 Jaccard). Operates on
    `title_en` if present, else `title`. Pre-translate via translate_items()
    before calling so cross-language duplicates merge."""
    groups: list[list[dict]] = []
    group_words: list[set] = []
    for item in items:
        words = title_words(item.get("title_en") or item.get("title", ""))
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
    return groups


def merge_rss(items: list[dict]) -> list[dict]:
    """
    Merge/dedup RSS items. Score = cross_source_count × authority × recency.
    No z-score — cross-source mention count is the engagement signal for RSS.
    """
    translate_items(items)
    groups = _group_by_title(items)

    results = []
    for group in groups:
        sources = list({i["source"] for i in group})
        if len(sources) < 2:
            continue

        canonical = max(group, key=lambda x: len(x.get("summary", "")))
        canonical = dict(canonical)

        canonical["sources"] = sources
        canonical["mention_count"] = len(group)

        cross_bonus = math.log1p(len(sources) - 1)
        authority = max(SOURCE_AUTHORITY.get(s, DEFAULT_AUTHORITY) for s in sources)
        recency = recency_score(canonical.get("published_at"))

        canonical["score"] = round((1 + cross_bonus) * authority * recency, 4)
        results.append(canonical)

    return results


def dedup_section(items: list[dict]) -> list[dict]:
    """Merge near-duplicate section items by title similarity. Keeps the
    highest-engagement representative per group; no re-scoring."""
    translate_items(items)
    groups = _group_by_title(items)
    return [
        max(g, key=lambda x: x.get("engagement", x.get("score", 0)) or 0)
        for g in groups
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="Top N RSS items (default: 5)")
    parser.add_argument("--section-limit", type=int, default=5, help="Top N per non-RSS section (default: 5)")
    parser.add_argument("--output", help="Write output to FILE instead of stdout")
    parser.add_argument("--mode", default="tech", choices=["tech", "science", "news", "finance"], help="Digest mode (default: tech)")
    args = parser.parse_args()

    fetchers = FETCHERS[args.mode]
    rss_items = []
    sections = {}

    section_pools: dict[str, list[dict]] = {}

    section_limits: dict[str, int] = {}
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
            if "section_limit" in fetcher:
                section_limits[section] = fetcher["section_limit"]
            print(f"  {section}: +{len(items)} items", file=sys.stderr)

    for section, pool in section_pools.items():
        # Dedup by URL first to drop exact-link repeats, then by title similarity
        # (translation-aware) so the same story from different sources/languages merges.
        seen_urls = set()
        url_unique = []
        for item in pool:
            url = item.get("url", "")
            if not url or url not in seen_urls:
                if url:
                    seen_urls.add(url)
                url_unique.append(item)
        deduped = dedup_section(url_unique)
        deduped.sort(key=lambda x: x.get("engagement", x.get("score", 0)) or 0, reverse=True)
        top = deduped[:section_limits.get(section, args.section_limit)]
        if top:
            sections[section] = top
        print(f"  {section}: {len(top)} unique items (from {len(pool)} pooled, {len(url_unique)} after URL dedup)", file=sys.stderr)

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
