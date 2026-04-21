#!/usr/bin/env python3
"""
Curation — scores items by relevance using Claude, then re-ranks.

For non-English items (news mode), Claude also translates titles/summaries to English.

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
    "tech": (
        "AI/ML breakthroughs, open-source projects, developer tools, startups, "
        "cloud infrastructure, programming languages, security vulnerabilities, "
        "chip/hardware news, science with practical applications."
    ),
    "news": (
        "Major world events, geopolitics, wars and conflicts, elections and democracy, "
        "economic policy, markets and finance, climate and environment, health and medicine, "
        "science discoveries, social movements, and high-impact cultural events."
    ),
}


def curate_batch(items: list[dict], mode: str) -> list[dict]:
    profile = INTEREST_PROFILES.get(mode, INTEREST_PROFILES["tech"])
    translate = mode == "news"

    compact = [
        {
            "index": i,
            "title": item["title"],
            "summary": item.get("summary", "")[:200],
            "source": item.get("source", ""),
        }
        for i, item in enumerate(items)
    ]

    translate_instruction = (
        " If the title or summary is not in English, translate them to English first, "
        "then score. Include the translated title in your response as 'title_en'."
        if translate else ""
    )

    prompt = (
        f"You are curating a digest for someone interested in: {profile}\n\n"
        f"Score each item 0.0–1.0 for relevance to that interest profile.{translate_instruction}\n"
        f"Return ONLY a JSON array. Each object must have:\n"
        f"  'index' (int), 'relevance' (float 0-1)"
        + (", 'title_en' (string, English title — same as title if already English)" if translate else "")
        + f"\n\nItems:\n{json.dumps(compact, ensure_ascii=False)}"
    )

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    result = subprocess.run(
        [CLAUDE_PATH, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        print(f"  Claude error: {result.stderr[-200:]}", file=sys.stderr)
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
        if translate and "title_en" in s:
            item["title_en"] = s["title_en"]
        # Re-score: engagement * (0.3 + 0.7 * relevance)
        base = item.get("score", 0.0)
        item["score"] = round(base * (0.3 + 0.7 * relevance), 4)

    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="tech", choices=["tech", "news"], help="Interest profile (default: tech)")
    parser.add_argument("--top", type=int, default=50, help="Max items to curate (default: 50)")
    parser.add_argument("--input", help="Read items from FILE instead of stdin")
    parser.add_argument("--output", help="Write output to FILE instead of stdout")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            items = json.load(f)
    else:
        items = json.load(sys.stdin)

    # Only curate the top N by raw score to keep Claude prompt small
    items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)[:args.top]

    print(f"  Curating {len(items)} items (mode={args.mode})...", file=sys.stderr)
    items = curate_batch(items, args.mode)
    items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
    print(f"  Curation done.", file=sys.stderr)

    output = json.dumps(items, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
