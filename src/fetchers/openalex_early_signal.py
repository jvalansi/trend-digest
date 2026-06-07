#!/usr/bin/env python3
"""
OpenAlex early-signal fetcher — daily batch sweep of academic topics.

Uses the OpenAlex Topics API (4,516 topics, full sweep in ~5 days at 1,000/day).
Each topic has a clean domain hierarchy: domain → field → subfield → topic.
Surfaces topics with ≥200 papers in 2024 and 5–50× growth since 2019.
Always emits one item per domain group, even when nothing found.

State file:  data/openalex_sweep_state.json
Topic cache: data/openalex_topics.json  (refreshed every 30 days)

Usage:
  python fetchers/openalex_early_signal.py [--batch-size N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

DATA_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
TOPICS_CACHE = os.path.join(DATA_DIR, "openalex_topics.json")
STATE_FILE   = os.path.join(DATA_DIR, "openalex_sweep_state.json")

BASE   = "https://api.openalex.org"
MAILTO = "jvalansi1@gmail.com"

MIN_PAPERS_2024 = 200
MIN_RATIO       = 5.0
MAX_RATIO       = 50.0   # above this is likely a bulk tag-reassignment artifact


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": f"trend-digest/1.0 (mailto:{MAILTO})"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def load_or_refresh_topics() -> list[dict]:
    if os.path.exists(TOPICS_CACHE):
        age_days = (time.time() - os.path.getmtime(TOPICS_CACHE)) / 86400
        if age_days < 30:
            with open(TOPICS_CACHE) as f:
                topics = json.load(f)
            print(f"  Loaded {len(topics)} cached topics ({age_days:.0f}d old)", file=sys.stderr)
            return topics

    print("  Fetching all topics from OpenAlex...", file=sys.stderr)
    topics = []
    page = 1
    while True:
        params = urllib.parse.urlencode({
            "per-page": 200,
            "page": page,
            "select": "id,display_name,domain,field,subfield",
            "mailto": MAILTO,
        })
        data = fetch_json(f"{BASE}/topics?{params}")
        results = data.get("results", [])
        if not results:
            break
        for t in results:
            topics.append({
                "id":       t["id"],
                "name":     t["display_name"],
                "domain":   t["domain"]["display_name"],
                "domain_id": t["domain"]["id"],
                "field":    t["field"]["display_name"],
            })
        total = data["meta"]["count"]
        print(f"  ... {len(topics)}/{total} topics fetched", file=sys.stderr)
        if len(topics) >= total:
            break
        page += 1
        time.sleep(0.05)

    with open(TOPICS_CACHE, "w") as f:
        json.dump(topics, f)
    print(f"  Cached {len(topics)} topics", file=sys.stderr)
    return topics


def count_papers(topic_id: str, year: int) -> int:
    params = urllib.parse.urlencode({
        "filter": f"topics.id:{topic_id},publication_year:{year}",
        "per-page": 1,
        "select": "id",
        "mailto": MAILTO,
    })
    try:
        data = fetch_json(f"{BASE}/works?{params}")
        return int(data["meta"]["count"])
    except Exception:
        return -1


def check_topic(topic: dict) -> dict | None:
    tid = topic["id"]
    n2024 = count_papers(tid, 2024)
    if n2024 < MIN_PAPERS_2024:
        return None
    n2019 = count_papers(tid, 2019)
    if n2019 < 0 or n2024 < 0:
        return None
    ratio = n2024 / max(n2019, 1)
    if ratio < MIN_RATIO or ratio > MAX_RATIO:
        return None
    return {
        "name":      topic["name"],
        "id":        topic["id"],
        "domain":    topic["domain"],
        "domain_id": topic["domain_id"],
        "field":     topic["field"],
        "n2019":     n2019,
        "n2024":     n2024,
        "ratio":     ratio,
    }


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"offset": 0, "cycle": 1}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=1000, help="Topics to scan per run (default: 1000)")
    args = parser.parse_args()

    topics = load_or_refresh_topics()
    state  = load_state()
    offset = state["offset"]
    batch  = topics[offset: offset + args.batch_size]

    print(f"  Sweeping topics {offset}–{offset + len(batch) - 1} of {len(topics)} (cycle {state['cycle']})", file=sys.stderr)

    # Count topics per domain for this batch
    domain_meta: dict[str, dict] = {}
    domain_sizes: dict[str, int] = defaultdict(int)
    for t in batch:
        d = t["domain"]
        domain_sizes[d] += 1
        if d not in domain_meta:
            domain_meta[d] = {"id": t["domain_id"]}

    # Check all topics in parallel
    hits_by_domain: dict[str, list] = defaultdict(list)
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(check_topic, t): t for t in batch}
        for future in as_completed(futures):
            result = future.result()
            if result:
                hits_by_domain[result["domain"]].append(result)

    # Advance state
    next_offset = offset + args.batch_size
    if next_offset >= len(topics):
        state["offset"] = 0
        state["cycle"]  = state.get("cycle", 1) + 1
        print(f"  Full sweep complete — starting cycle {state['cycle']}", file=sys.stderr)
    else:
        state["offset"] = next_offset
    state["last_run"] = datetime.now(timezone.utc).date().isoformat()
    save_state(state)

    total_hits = sum(len(v) for v in hits_by_domain.values())
    print(f"  {total_hits} early signals across {len(domain_sizes)} domains", file=sys.stderr)

    now = datetime.now(timezone.utc).isoformat()
    items = []

    # One item per domain — domains with signals first (by max ratio), then empty ones
    def domain_sort_key(domain):
        hits = hits_by_domain.get(domain, [])
        return (-max((h["ratio"] for h in hits), default=0), domain)

    for domain in sorted(domain_sizes.keys(), key=domain_sort_key):
        hits       = sorted(hits_by_domain.get(domain, []), key=lambda h: h["ratio"], reverse=True)
        n_scanned  = domain_sizes[domain]
        domain_url = domain_meta[domain]["id"].replace("https://openalex.org/domains/", "https://openalex.org/domains/")

        if hits:
            parts    = [f"{h['name']} ({h['field']}): {h['n2019']:,}→{h['n2024']:,} ({h['ratio']:.1f}×)" for h in hits[:5]]
            summary  = " | ".join(parts)
            title    = f"{domain} — {len(hits)} signal{'s' if len(hits) != 1 else ''}"
            engagement = max(h["ratio"] for h in hits)
        else:
            title      = f"{domain} — nothing found"
            summary    = f"Scanned {n_scanned} topics. No acceleration signals (≥{MIN_PAPERS_2024} papers in 2024, {MIN_RATIO:.0f}–{MAX_RATIO:.0f}× growth since 2019)."
            engagement = 0.0

        items.append({
            "title":        title,
            "summary":      summary,
            "url":          domain_url,
            "source":       "OpenAlex Early Signal",
            "category":     "science",
            "engagement":   round(engagement, 2),
            "fetched_at":   now,
            "published_at": None,
        })

    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
