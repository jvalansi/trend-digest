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
        # Re-score: base * (0.3 + 0.7 * relevance). Sections fetchers strip
        # `score` in stats.py and expose `engagement` (z-score) instead, so
        # fall back to that. Clamp at 0 because engagement z-scores can be
        # negative — without this, multiplying by a sub-1 factor would
        # invert the ranking (less-engaging items would beat more-engaging ones).
        base = item.get("score")
        if base is None:
            base = max(0.0, item.get("engagement", 0.0))
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
        sections = data.get("sections", {})
        for name, items in sections.items():
            if not items:
                continue
            print(f"  Curating {len(items)} items in section '{name}'...", file=sys.stderr)
            curated = curate_batch(items, args.mode)
            sections[name] = sorted(curated, key=lambda x: x.get("score", 0), reverse=True)
        output_data = {"rss": rss, "sections": sections}
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
