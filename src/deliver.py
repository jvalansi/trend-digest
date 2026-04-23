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


def format_section(name: str, items: list[dict]) -> str:
    """Format a per-source section as a single Slack message block."""
    lines = [f"*{name}*"]
    for item in items:
        title = item.get("title_en") or item["title"]
        url = item["url"]
        raw = item.get("engagement_raw")
        metric = f" — {int(raw):,}" if raw else ""
        lines.append(f"• <{url}|{title}>{metric}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Read items from FILE instead of stdin")
    parser.add_argument("--dry-run", action="store_true", help="Print message without posting")
    parser.add_argument("--mode", default="tech", choices=["tech", "news"], help="Digest mode (default: tech)")
    parser.add_argument("--channel", help="Slack channel override")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%A, %B %-d")
    label = "News Digest" if args.mode == "news" else "Trend Digest"
    channel = args.channel or (NEWS_CHANNEL if args.mode == "news" else SLACK_CHANNEL)

    # New sectioned format
    if isinstance(data, dict) and "rss" in data:
        items = data["rss"]
        sections = data.get("sections", {})
    else:
        items = data
        sections = {}

    if not items and not sections:
        print("No items to deliver.", file=sys.stderr)
        return

    print("Generating descriptions...", file=sys.stderr)
    descriptions = generate_descriptions(items, args.mode)
    formatted_rss = [format_item(item, desc) for item, desc in zip(items, descriptions)]
    formatted_sections = [format_section(name, sec_items) for name, sec_items in sections.items()]

    total = len(items) + sum(len(v) for v in sections.values())
    header = f"*{label} — {date_str}* ({len(items)} stories" + (f" + {len(sections)} source digests)" if sections else ")")

    if args.dry_run:
        print(header)
        for msg in formatted_rss:
            print("\n---\n" + msg)
        for msg in formatted_sections:
            print("\n---\n" + msg)
        return

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    thread_ts = post_to_slack(header, token, channel)
    for msg in formatted_rss:
        post_to_slack(msg, token, channel, thread_ts=thread_ts, unfurl=True)
    for msg in formatted_sections:
        post_to_slack(msg, token, channel, thread_ts=thread_ts)
    print(f"Posted {len(items)} RSS + {len(sections)} sections to #{channel}", file=sys.stderr)


if __name__ == "__main__":
    main()
