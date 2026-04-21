#!/usr/bin/env python3
"""
Delivery — formats aggregated items and posts to Slack.

Usage:
  python aggregate.py | python deliver.py
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
NEWS_CHANNEL = os.environ.get("NEWS_DIGEST_CHANNEL", "proj-news-digest")
CLAUDE_PATH = os.environ.get("CLAUDE_PATH", "/home/ubuntu/.local/bin/claude")


def generate_descriptions(items: list[dict], mode: str = "tech") -> list[str]:
    """Ask Claude to write a one-sentence description for each item."""
    compact = [
        {
            "index": i,
            "title": item.get("title_en") or item["title"],
            "summary": item.get("summary", "")[:300],
        }
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


def format_item(item: dict, description: str) -> str:
    sources = item.get("sources", [item["source"]])
    source_str = " · ".join(sources)
    title = item.get("title_en") or item["title"]
    url = item["url"]
    desc_str = f"\n   {description}" if description else ""
    raw = item.get("engagement_raw")
    eng = item.get("engagement")
    engagement_str = ""
    if raw is not None and eng is not None:
        engagement_str = f" · {int(raw)} pts · z={eng:+.2f}"
    return f"*<{url}|{title}>*{desc_str}\n   _{source_str}{engagement_str}_"


def post_to_slack(text: str, token: str, channel: str, thread_ts: str | None = None, unfurl: bool = False) -> str:
    """Post a message and return its ts."""
    body: dict = {"channel": channel, "text": text, "unfurl_links": unfurl, "unfurl_media": unfurl}
    if thread_ts:
        body["thread_ts"] = thread_ts
    payload = json.dumps(body).encode()
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
    return result["ts"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Read items from FILE instead of stdin")
    parser.add_argument("--dry-run", action="store_true", help="Print message without posting")
    parser.add_argument("--mode", default="tech", choices=["tech", "news"], help="Digest mode (default: tech)")
    parser.add_argument("--channel", help="Slack channel override")
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
    label = "News Digest" if args.mode == "news" else "Trend Digest"
    channel = args.channel or (NEWS_CHANNEL if args.mode == "news" else SLACK_CHANNEL)

    print("Generating descriptions...", file=sys.stderr)
    descriptions = generate_descriptions(items, args.mode)
    formatted = [format_item(item, desc) for item, desc in zip(items, descriptions)]

    if args.dry_run:
        print(f"*{label} — {date_str}* ({len(items)} items)")
        for msg in formatted:
            print("\n---\n" + msg)
        return

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    thread_ts = post_to_slack(f"*{label} — {date_str}* ({len(items)} items)", token, channel)
    for msg in formatted:
        post_to_slack(msg, token, channel, thread_ts=thread_ts, unfurl=True)
    print(f"Posted {len(items)} items to #{channel}", file=sys.stderr)


if __name__ == "__main__":
    main()
