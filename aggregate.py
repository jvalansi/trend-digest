#!/usr/bin/env python3
"""
Aggregator — runs all fetchers, merges output, scores, and ranks.

Scoring for RSS items (which have no native engagement signal):
  - Cross-source mentions: each additional source covering the same story adds weight
  - Source authority: baseline weight per domain based on traffic rank
  - Recency decay: score halves every 12 hours

Usage:
  python aggregate.py [--limit N] [--output FILE]

Output: JSON array of top N items, sorted by final score.
"""

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone

PYTHON = sys.executable

# Authority weights by source name (higher = more authoritative)
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
    "GitHub Trending": 1.1,
}
DEFAULT_AUTHORITY = 0.8

FETCHERS = [
    {"cmd": ["python", "fetchers/rss.py", "--limit", "20"]},
    {"cmd": ["python", "fetchers/hn.py", "--feed", "top", "--limit", "30"]},
    {"cmd": ["python", "fetchers/youtube.py", "--mode", "channels", "--limit", "5"]},
    {"cmd": ["python", "fetchers/github.py", "--limit", "25"]},
]


def run_fetcher(cmd: list[str]) -> list[dict]:
    result = subprocess.run(
        [PYTHON if c == "python" else c for c in cmd],
        capture_output=True, text=True, cwd=os.path.dirname(__file__)
    )
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            print(f"  {line}", file=sys.stderr)
    if result.returncode != 0:
        print(f"  ERROR running {cmd[1]}: {result.stderr[-200:]}", file=sys.stderr)
        return []
    return json.loads(result.stdout)


def title_words(title: str) -> set[str]:
    stopwords = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "was"}
    return {w for w in title.lower().split() if w not in stopwords and len(w) > 2}


def similarity(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def recency_score(published_at: str | None) -> float:
    """Returns a multiplier in (0, 1] based on age. Halves every 12h."""
    if not published_at:
        return 0.5
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        return math.exp(-age_hours * math.log(2) / 12)
    except Exception:
        return 0.5


def merge_and_score(items: list[dict]) -> list[dict]:
    """
    Group near-duplicate items, merge them into one, and compute a final score:
      score = (engagement_z + cross_source_bonus) * authority * recency
    """
    groups: list[list[dict]] = []
    group_words: list[set] = []

    for item in items:
        words = title_words(item["title"])
        matched = None
        for i, gw in enumerate(group_words):
            if similarity(words, gw) > 0.55:
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
        # Pick the item with the longest summary as canonical
        canonical = max(group, key=lambda x: len(x.get("summary", "")))
        canonical = dict(canonical)

        sources = list({i["source"] for i in group})
        canonical["sources"] = sources
        canonical["mention_count"] = len(group)

        # Cross-source bonus: log scale so 2 sources ≠ 2x score
        cross_bonus = math.log1p(len(group) - 1)

        # Authority: max authority among sources that covered it
        authority = max(SOURCE_AUTHORITY.get(s, DEFAULT_AUTHORITY) for s in sources)

        # Recency
        recency = recency_score(canonical.get("published_at"))

        base_engagement = canonical.get("engagement", 0.0)
        canonical["score"] = round((base_engagement + cross_bonus) * authority * recency, 4)

        results.append(canonical)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Top N items to return (default: 20)")
    parser.add_argument("--output", help="Write output to FILE instead of stdout")
    args = parser.parse_args()

    all_items = []
    for fetcher in FETCHERS:
        print(f"\n[{fetcher['cmd'][1]}]", file=sys.stderr)
        items = run_fetcher(fetcher["cmd"])
        all_items.extend(items)
        print(f"  Subtotal: {len(all_items)} items", file=sys.stderr)

    print(f"\nTotal raw items: {len(all_items)}", file=sys.stderr)
    scored = merge_and_score(all_items)
    print(f"After merging: {len(scored)} unique stories", file=sys.stderr)

    ranked = sorted(scored, key=lambda x: x["score"], reverse=True)
    top = ranked[:args.limit]

    output = json.dumps(top, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\nWrote {len(top)} items to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
