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
FINANCE_CHANNEL = os.environ.get("FINANCE_DIGEST_CHANNEL", SLACK_CHANNEL)
CLAUDE_PATH = os.environ.get("CLAUDE_PATH", "/home/ubuntu/.local/bin/claude")

REDDIT_SUBREDDITS = {
    "tech": ["artificial", "MachineLearning", "programming", "technology"],
    "news": ["worldnews", "geopolitics"],
    "finance": ["investing", "stocks", "economics"],
}


def format_as_markdown(label: str, date_str: str, items: list[dict], descriptions: list[str], sections: dict, section_descs: list[str]) -> str:
    """Format digest items as a Markdown document for publishing."""
    lines = [f"# {label} — {date_str}\n"]
    for item, desc in zip(items, descriptions):
        title = item.get("title_en") or item["title"]
        url = item["url"]
        sources = " · ".join(item.get("sources", [item["source"]]))
        lines.append(f"### [{title}]({url})")
        if desc:
            lines.append(f"{desc}")
        lines.append(f"*{sources}*\n")
    desc_idx = 0
    for name, sitems in sections.items():
        lines.append(f"## {name}\n")
        for item in sitems:
            title = item.get("title_en") or item["title"]
            url = item["url"]
            sources = " · ".join(item.get("sources", [item["source"]]))
            desc = section_descs[desc_idx] if desc_idx < len(section_descs) else ""
            desc_idx += 1
            lines.append(f"### [{title}]({url})")
            if desc:
                lines.append(f"{desc}")
            lines.append(f"*{sources}*\n")
    return "\n".join(lines)


def generate_social_teaser(items: list[dict], label: str) -> str:
    """Ask Claude to write a 2-sentence social media teaser for the digest."""
    top = [{"title": item.get("title_en") or item["title"]} for item in items[:5]]
    prompt = (
        f"Write a 2-sentence social media post teasing today's {label}. "
        "Be specific, mention 1-2 topics, and end with a hook. "
        "Plain text only, no hashtags, no emojis, no quotes.\n\n"
        f"Top stories: {json.dumps(top, ensure_ascii=False)}"
    )
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    result = subprocess.run(
        [CLAUDE_PATH, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        return f"Today's {label} is live."
    return json.loads(result.stdout).get("result", "").strip()


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


def _publish_to_socials(label, date_str, rss_items, rss_descs, sections, section_descs, mode):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from publishers import medium, bluesky, linkedin, reddit

    all_items = rss_items + [item for items in sections.values() for item in items]
    title = f"{label} — {date_str}"
    content_md = format_as_markdown(label, date_str, rss_items, rss_descs, sections, section_descs)
    teaser = generate_social_teaser(all_items, label)

    medium_token = os.environ.get("MEDIUM_TOKEN")
    post_url = None
    if medium_token:
        try:
            post_url = medium.publish(title, content_md, medium_token)
            print(f"Published to Medium: {post_url}", file=sys.stderr)
        except Exception as e:
            print(f"Medium publish failed: {e}", file=sys.stderr)
    else:
        print("MEDIUM_TOKEN not set — skipping Medium", file=sys.stderr)

    if not post_url:
        print("No publish URL — skipping social shares", file=sys.stderr)
        return

    bsky_handle = os.environ.get("BSKY_HANDLE")
    bsky_password = os.environ.get("BSKY_APP_PASSWORD")
    if bsky_handle and bsky_password:
        try:
            bluesky.post(teaser, post_url, title, teaser, bsky_handle, bsky_password)
            print("Posted to Bluesky", file=sys.stderr)
        except Exception as e:
            print(f"Bluesky post failed: {e}", file=sys.stderr)
    else:
        print("BSKY_HANDLE/BSKY_APP_PASSWORD not set — skipping Bluesky", file=sys.stderr)

    li_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    li_urn = os.environ.get("LINKEDIN_PERSON_URN")
    if li_token and li_urn:
        try:
            linkedin.post(teaser, post_url, title, li_token, li_urn)
            print("Posted to LinkedIn", file=sys.stderr)
        except Exception as e:
            print(f"LinkedIn post failed: {e}", file=sys.stderr)
    else:
        print("LINKEDIN_ACCESS_TOKEN/LINKEDIN_PERSON_URN not set — skipping LinkedIn", file=sys.stderr)

    reddit_id = os.environ.get("REDDIT_CLIENT_ID")
    reddit_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    reddit_user = os.environ.get("REDDIT_USERNAME")
    reddit_pass = os.environ.get("REDDIT_PASSWORD")
    if reddit_id and reddit_secret and reddit_user and reddit_pass:
        subreddits = REDDIT_SUBREDDITS.get(mode, REDDIT_SUBREDDITS["tech"])
        try:
            reddit.post(title, post_url, subreddits, reddit_id, reddit_secret, reddit_user, reddit_pass)
            print(f"Posted to Reddit: {subreddits}", file=sys.stderr)
        except Exception as e:
            print(f"Reddit post failed: {e}", file=sys.stderr)
    else:
        print("Reddit credentials not set — skipping Reddit", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Read items from FILE instead of stdin")
    parser.add_argument("--dry-run", action="store_true", help="Print message without posting")
    parser.add_argument("--mode", default="tech", choices=["tech", "news", "finance"], help="Digest mode (default: tech)")
    parser.add_argument("--channel", help="Slack channel override")
    parser.add_argument("--publish", action="store_true", help="Publish to Medium and share on Bluesky, LinkedIn, Reddit")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%A, %B %-d")
    if args.mode == "news":
        label = "News Digest"
        channel = args.channel or NEWS_CHANNEL
    elif args.mode == "finance":
        label = "Finance Digest"
        channel = args.channel or FINANCE_CHANNEL
    else:
        label = "Tech Digest"
        channel = args.channel or SLACK_CHANNEL

    # New sectioned format
    if isinstance(data, dict) and "rss" in data:
        rss_items = data["rss"]
        sections = data.get("sections", {})
    else:
        rss_items = data
        sections = {}

    # Flatten all items for description generation
    section_items = [(name, item) for name, items in sections.items() for item in items]
    all_items = rss_items + [item for _, item in section_items]

    if not all_items:
        print("No items to deliver.", file=sys.stderr)
        return

    print("Generating descriptions...", file=sys.stderr)
    descriptions = generate_descriptions(all_items, args.mode)
    rss_descs = descriptions[:len(rss_items)]
    section_descs = descriptions[len(rss_items):]

    formatted_rss = [format_item(item, desc) for item, desc in zip(rss_items, rss_descs)]

    # Group section messages: header per section, then one message per item
    section_messages = []
    desc_idx = 0
    for name, items in sections.items():
        section_messages.append(f"*{name}*")
        for item in items:
            section_messages.append(format_item(item, section_descs[desc_idx]))
            desc_idx += 1

    total_items = len(rss_items) + len(section_items)
    header = f"*{label} — {date_str}* ({total_items} items)"

    if args.dry_run:
        print(header)
        for msg in formatted_rss:
            print("\n---\n" + msg)
        for msg in section_messages:
            print("\n---\n" + msg)
        return

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    thread_ts = post_to_slack(header, token, channel)
    for msg in formatted_rss:
        post_to_slack(msg, token, channel, thread_ts=thread_ts, unfurl=True)
    for msg in section_messages:
        post_to_slack(msg, token, channel, thread_ts=thread_ts, unfurl=True)
    print(f"Posted {total_items} items to #{channel}", file=sys.stderr)

    if args.publish:
        _publish_to_socials(label, date_str, rss_items, rss_descs, sections, section_descs, args.mode)


if __name__ == "__main__":
    main()
