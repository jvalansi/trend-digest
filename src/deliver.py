#!/usr/bin/env python3
"""
Delivery — formats curated items and posts to Slack.

Usage:
  python aggregate.py | python curate.py | python deliver.py
  python deliver.py --input FILE
  python deliver.py --input FILE --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request

SLACK_CHANNEL = os.environ.get("TREND_DIGEST_CHANNEL", "proj-trend-digest")
CLAUDE_PATH = os.environ.get("CLAUDE_PATH", "/home/ubuntu/.local/bin/claude")


def generate_descriptions(items: list[dict]) -> list[str]:
    """Ask Claude to write a one-sentence description for each item."""
    compact = [
        {"index": i, "title": item["title"], "summary": item.get("summary", "")[:300]}
        for i, item in enumerate(items)
    ]
    prompt = (
        "Write a single plain-text sentence (max 20 words) describing each news item below. "
        "Be specific and factual. Return ONLY a JSON array of objects with 'index' and 'description' fields.\n\n"
        + json.dumps(compact, ensure_ascii=False)
    )
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    result = subprocess.run(
        [CLAUDE_PATH, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        return [""] * len(items)
    response_text = json.loads(result.stdout).get("result", "")
    start, end = response_text.find("["), response_text.rfind("]") + 1
    descs = json.loads(response_text[start:end])
    desc_map = {d["index"]: d["description"] for d in descs}
    return [desc_map.get(i, "") for i in range(len(items))]


def format_item(i: int, item: dict, description: str) -> str:
    sources = item.get("sources", [item["source"]])
    source_str = " · ".join(sources)
    title = item["title"]
    url = item["url"]
    desc_str = f"\n   {description}" if description else ""
    raw = item.get("engagement_raw")
    eng = item.get("engagement")
    engagement_str = ""
    if raw is not None and eng is not None:
        engagement_str = f" · {int(raw)} pts · z={eng:+.2f}"
    return f"{i}. *<{url}|{title}>*{desc_str}\n   _{source_str}{engagement_str}_"


def post_to_slack(text: str, token: str, channel: str) -> None:
    payload = json.dumps({"channel": channel, "text": text, "unfurl_links": False}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        print(f"Slack error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Read items from FILE instead of stdin")
    parser.add_argument("--dry-run", action="store_true", help="Print message without posting")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            items = json.load(f)
    else:
        items = json.load(sys.stdin)

    if not items:
        print("No items to deliver.", file=sys.stderr)
        return

    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%A, %B %-d")
    lines = [f"*Trend Digest — {date_str}*\n"]
    print("Generating descriptions...", file=sys.stderr)
    descriptions = generate_descriptions(items)
    for i, (item, desc) in enumerate(zip(items, descriptions), 1):
        lines.append(format_item(i, item, desc))

    message = "\n\n".join(lines)

    if args.dry_run:
        print(message)
        return

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    post_to_slack(message, token, SLACK_CHANNEL)
    print(f"Posted {len(items)} items to #{SLACK_CHANNEL}", file=sys.stderr)


if __name__ == "__main__":
    main()
