#!/usr/bin/env python3
"""
OpenAlex early-signal fetcher — daily batch sweep of level-3 academic concepts.

Processes ~1,000 concepts/day, cycling through all ~24,749 level-3 concepts in ~25 days.
Surfaces concepts with ≥200 papers in 2024 and 5–50× growth since 2019.

State file:    data/openalex_sweep_state.json
Concept cache: data/openalex_concepts_l3.json  (refreshed every 30 days)

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

DATA_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
CONCEPTS_CACHE = os.path.join(DATA_DIR, "openalex_concepts_l3.json")
STATE_FILE     = os.path.join(DATA_DIR, "openalex_sweep_state.json")

BASE   = "https://api.openalex.org"
MAILTO = "jvalansi1@gmail.com"

MIN_PAPERS_2024 = 200
MIN_RATIO       = 5.0
MAX_RATIO       = 50.0   # above this is likely a bulk tag-reassignment artifact


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": f"trend-digest/1.0 (mailto:{MAILTO})"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def load_or_refresh_concepts() -> list[dict]:
    if os.path.exists(CONCEPTS_CACHE):
        age_days = (time.time() - os.path.getmtime(CONCEPTS_CACHE)) / 86400
        if age_days < 30:
            with open(CONCEPTS_CACHE) as f:
                concepts = json.load(f)
            print(f"  Loaded {len(concepts)} cached concepts ({age_days:.0f}d old)", file=sys.stderr)
            return concepts

    print("  Fetching all level-3 concepts from OpenAlex (first run or monthly refresh)...", file=sys.stderr)
    concepts = []
    cursor = "*"
    while cursor:
        params = urllib.parse.urlencode({
            "filter": "level:3",
            "per-page": 200,
            "cursor": cursor,
            "select": "id,display_name",
            "mailto": MAILTO,
        })
        data = fetch_json(f"{BASE}/concepts?{params}")
        for c in data.get("results", []):
            concepts.append({"id": c["id"], "name": c["display_name"]})
        cursor = data.get("meta", {}).get("next_cursor")
        print(f"  ... {len(concepts)} concepts fetched", file=sys.stderr)
        time.sleep(0.1)

    with open(CONCEPTS_CACHE, "w") as f:
        json.dump(concepts, f)
    print(f"  Cached {len(concepts)} level-3 concepts to {CONCEPTS_CACHE}", file=sys.stderr)
    return concepts


def count_papers(concept_id: str, year: int) -> int:
    params = urllib.parse.urlencode({
        "filter": f"concepts.id:{concept_id},publication_year:{year}",
        "per-page": 1,
        "select": "id",
        "mailto": MAILTO,
    })
    try:
        data = fetch_json(f"{BASE}/works?{params}")
        return int(data["meta"]["count"])
    except Exception:
        return -1


def check_concept(concept: dict) -> dict | None:
    cid = concept["id"]
    n2024 = count_papers(cid, 2024)
    if n2024 < MIN_PAPERS_2024:
        return None
    n2019 = count_papers(cid, 2019)
    if n2019 < 0 or n2024 < 0:
        return None
    ratio = n2024 / max(n2019, 1)
    if ratio < MIN_RATIO or ratio > MAX_RATIO:
        return None
    return {"name": concept["name"], "id": cid, "n2019": n2019, "n2024": n2024, "ratio": ratio}


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
    parser.add_argument("--batch-size", type=int, default=1000, help="Concepts to scan per run (default: 1000)")
    args = parser.parse_args()

    concepts = load_or_refresh_concepts()
    state    = load_state()
    offset   = state["offset"]
    batch    = concepts[offset: offset + args.batch_size]

    print(f"  Sweeping concepts {offset}–{offset + len(batch) - 1} of {len(concepts)} (cycle {state['cycle']})", file=sys.stderr)

    hits = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(check_concept, c): c for c in batch}
        for future in as_completed(futures):
            result = future.result()
            if result:
                hits.append(result)

    next_offset = offset + args.batch_size
    if next_offset >= len(concepts):
        state["offset"] = 0
        state["cycle"]  = state.get("cycle", 1) + 1
        print(f"  Full sweep complete — starting cycle {state['cycle']}", file=sys.stderr)
    else:
        state["offset"] = next_offset
    state["last_run"] = datetime.now(timezone.utc).date().isoformat()
    save_state(state)

    hits.sort(key=lambda x: x["ratio"], reverse=True)
    print(f"  {len(hits)} early signals in batch of {len(batch)}", file=sys.stderr)

    now   = datetime.now(timezone.utc).isoformat()
    items = []
    for h in hits:
        concept_slug = h["id"].split("/")[-1]
        items.append({
            "title":        h["name"],
            "summary":      f"{h['n2019']:,} → {h['n2024']:,} papers (2019→2024, {h['ratio']:.1f}× growth)",
            "url":          f"https://openalex.org/concepts/{concept_slug}",
            "source":       "OpenAlex Early Signal",
            "category":     "science",
            "engagement":   round(h["ratio"], 2),
            "fetched_at":   now,
            "published_at": None,
        })

    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
