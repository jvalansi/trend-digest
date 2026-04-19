#!/usr/bin/env python3
"""
Curation layer — scores items against interest profile using Claude.

Usage:
  python aggregate.py | python curate.py [--limit N] [--min-score FLOAT]
  python curate.py --input FILE [--limit N] [--min-score FLOAT]

Output: JSON array of curated items with relevance scores, sorted by combined score.
"""

import argparse
import json
import os
import subprocess
import sys

CLAUDE_PATH = os.environ.get("CLAUDE_PATH", "/home/ubuntu/.local/bin/claude")

INTEREST_PROFILE = """
- AI / ML: research, tools, models, agents, LLMs, infrastructure
- Geopolitics: international relations, wars, elections, diplomacy, sanctions
- Science: longevity, biology, physics, space, climate, medicine
- Startups & tech products: launches, funding, acquisitions, new tools
- Finance & markets: stocks, crypto, macro trends, economic policy
- Self-improvement & productivity: career, learning, focus, health
"""

SYSTEM_PROMPT = """You are a content curator. Given a list of news items, score each one for relevance to the user's interest profile.

Interest profile:
""" + INTEREST_PROFILE + """

For each item, return a relevance score from 0.0 to 1.0:
- 1.0 = directly on-topic (e.g. new AI model release, major geopolitical event)
- 0.5 = tangentially related (e.g. general tech news)
- 0.0 = off-topic (e.g. sports, celebrity, lifestyle)

Return ONLY a JSON array of objects with "index" and "relevance" fields. No explanation."""


def curate(items: list[dict], limit: int, min_score: float) -> list[dict]:
    # Build a compact list for Claude to score
    compact = [
        {"index": i, "title": item["title"], "source": item["source"], "summary": item.get("summary", "")[:200]}
        for i, item in enumerate(items)
    ]

    prompt = SYSTEM_PROMPT + "\n\nItems to score:\n" + json.dumps(compact, ensure_ascii=False)
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    result = subprocess.run(
        [CLAUDE_PATH, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        print(f"Claude CLI error: {result.stderr[-300:]}", file=sys.stderr)
        sys.exit(1)

    response_text = json.loads(result.stdout).get("result", "")
    # Extract JSON array from response
    start = response_text.find("[")
    end = response_text.rfind("]") + 1
    scores = json.loads(response_text[start:end])
    score_map = {s["index"]: s["relevance"] for s in scores}

    results = []
    for i, item in enumerate(items):
        relevance = score_map.get(i, 0.0)
        if relevance < min_score:
            continue
        item = dict(item)
        item["relevance"] = relevance
        item["final_score"] = round(item.get("score", 0.0) * (0.3 + 0.7 * relevance), 4)
        results.append(item)

    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results[:limit]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Read items from FILE instead of stdin")
    parser.add_argument("--limit", type=int, default=20, help="Top N items after curation (default: 20)")
    parser.add_argument("--min-score", type=float, default=0.4, help="Minimum relevance score to include (default: 0.4)")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            items = json.load(f)
    else:
        items = json.load(sys.stdin)

    print(f"Curating {len(items)} items...", file=sys.stderr)
    results = curate(items, args.limit, args.min_score)
    print(f"Kept {len(results)} items after curation", file=sys.stderr)

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
