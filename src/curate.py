#!/usr/bin/env python3
"""
Curation — scores items by relevance using Claude, then re-ranks.

Translation is handled upstream by src/translate.py.

Final score:
  final_score = engagement_score * (0.3 + 0.7 * relevance)

Usage:
  python aggregate.py | python curate.py [--mode tech|news] [--top N]
  python curate.py --input FILE [--mode tech|news] [--top N]

Output: JSON array of curated items to stdout.
"""

import argparse
import json
import os
import subprocess
import sys

CLAUDE_PATH = os.environ.get("CLAUDE_PATH", "/home/ubuntu/.local/bin/claude")

INTEREST_PROFILES = {
    "science": (
        "Biology, genetics, genomics, neuroscience, medicine, clinical trials, "
        "physics, climate science, ecology, chemistry, space exploration, "
        "mathematics, preprints, and scientific breakthroughs across all disciplines."
    ),
    "tech": (
        "AI/ML breakthroughs, open-source projects, developer tools, startups, "
        "cloud infrastructure, programming languages, security vulnerabilities, "
        "chip/hardware news, science discoveries, biology, physics, medicine, "
        "climate science, space exploration, neuroscience."
    ),
    "news": (
        "Major world events, geopolitics, wars and conflicts, elections and democracy, "
        "economic policy, markets and finance, climate and environment, health and medicine, "
        "science discoveries, social movements, and high-impact cultural events."
    ),
    "finance": (
        "Financial markets, macroeconomics, geopolitical events affecting markets, "
        "unusual trading activity, commodity price moves, central bank policy, "
        "emerging market stress, sector rotation, prediction market odds shifts, "
        "and high-impact economic data releases."
    ),
}


def curate_batch(items: list[dict], mode: str) -> list[dict]:
    profile = INTEREST_PROFILES.get(mode, INTEREST_PROFILES["tech"])

    compact = [
        {
            "index": i,
            "title": item.get("title_en") or item["title"],
            "summary": (item.get("summary_en") or item.get("summary", ""))[:200],
            "source": item.get("source", ""),
        }
        for i, item in enumerate(items)
    ]

    prompt = (
        f"You are curating a digest for someone interested in: {profile}\n\n"
        f"Score each item 0.0–1.0 for relevance to that interest profile.\n"
        f"Return ONLY a JSON array. Each object must have:\n"
        f"  'index' (int), 'relevance' (float 0-1)"
        f"\n\nItems:\n{json.dumps(compact, ensure_ascii=False)}"
    )

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    result = subprocess.run(
        [CLAUDE_PATH, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"],
        input="", capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        print(f"  Claude error: rc={result.returncode} stderr={result.stderr[-300:]!r} "
              f"stdout={result.stdout[:500]!r}", file=sys.stderr)
        return items

    response_text = json.loads(result.stdout).get("result", "")
    start, end = response_text.find("["), response_text.rfind("]") + 1
    if start == -1:
        return items

    scores = json.loads(response_text[start:end])
    score_map = {s["index"]: s for s in scores}

    for i, item in enumerate(items):
        s = score_map.get(i, {})
        relevance = float(s.get("relevance", 0.5))
        item["relevance"] = round(relevance, 3)
        # Re-score: engagement * (0.3 + 0.7 * relevance)
        base = item.get("score", 0.0)
        item["score"] = round(base * (0.3 + 0.7 * relevance), 4)

    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="tech", choices=["tech", "science", "news", "finance"], help="Interest profile (default: tech)")
    parser.add_argument("--top", type=int, default=50, help="Max RSS items to curate (default: 50)")
    parser.add_argument("--input", help="Read items from FILE instead of stdin")
    parser.add_argument("--output", help="Write output to FILE instead of stdout")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    # New sectioned format: {"rss": [...], "sections": {...}}
    if isinstance(data, dict) and "rss" in data:
        rss = sorted(data["rss"], key=lambda x: x.get("score", 0), reverse=True)[:args.top]
        print(f"  Curating {len(rss)} RSS items (mode={args.mode})...", file=sys.stderr)
        rss = curate_batch(rss, args.mode)
        rss = sorted(rss, key=lambda x: x.get("score", 0), reverse=True)
        print(f"  Curation done.", file=sys.stderr)
        output_data = {"rss": rss, "sections": data.get("sections", {})}
    else:
        # Legacy flat list
        items = sorted(data, key=lambda x: x.get("score", 0), reverse=True)[:args.top]
        print(f"  Curating {len(items)} items (mode={args.mode})...", file=sys.stderr)
        items = curate_batch(items, args.mode)
        items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
        print(f"  Curation done.", file=sys.stderr)
        output_data = items

    output = json.dumps(output_data, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
