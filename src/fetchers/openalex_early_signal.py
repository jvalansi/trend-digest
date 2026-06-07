#!/usr/bin/env python3
"""
OpenAlex early-signal fetcher — daily batch sweep of level-3 academic concepts.

Processes ~1,000 concepts/day, cycling through all ~24,749 level-3 concepts in ~25 days.
Surfaces concepts with ≥200 papers in 2024 and 5–50× growth since 2019.

Always emits a batch summary item (even when nothing found) so the digest shows
sweep progress. Individual signal items are emitted for each hit.

State file:    data/openalex_sweep_state.json
Concept cache: data/openalex_concepts_l3.json  (refreshed every 30 days)

Usage:
  python fetchers/openalex_early_signal.py [--batch-size N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timezone

DATA_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
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

    print("  Fetching all level-3 concepts from OpenAlex...", file=sys.stderr)
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
    print(f"  Cached {len(concepts)} level-3 concepts", file=sys.stderr)
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
    return {"name": concept["name"], "id": concept["id"], "n2019": n2019, "n2024": n2024, "ratio": ratio}


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
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    concepts = load_or_refresh_concepts()
    state    = load_state()
    offset   = state["offset"]
    total    = len(concepts)

    now           = datetime.now(timezone.utc).isoformat()
    today         = date.today()
    current_month = today.strftime("%Y-%m")
    cycle_month   = state.get("cycle_month", "")

    # If the cycle just completed (offset reset to 0) and we're still in the same
    # month, wait — don't start the next cycle until the calendar month rolls over.
    if offset == 0 and cycle_month == current_month:
        next_m = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
        next_month_name = next_m.strftime("%B %Y")
        print(f"  Sweep complete for {current_month} — waiting for {next_month_name}", file=sys.stderr)
        items = [{
            "title":        f"Early signal sweep — waiting for {next_month_name}",
            "summary":      f"This month's full sweep of {total:,} concepts is complete (cycle {state['cycle'] - 1}). Next sweep starts in {next_month_name}.",
            "url":          "https://openalex.org/concepts",
            "source":       "OpenAlex Early Signal",
            "category":     "science",
            "engagement":   0.1,
            "fetched_at":   now,
            "published_at": None,
        }]
        print(json.dumps(items, ensure_ascii=False))
        return

    # Starting a new cycle (either first ever run, or the month has changed)
    if offset == 0:
        state["cycle_month"] = current_month

    batch    = concepts[offset: offset + args.batch_size]
    batch_num     = offset // args.batch_size + 1
    total_batches = math.ceil(total / args.batch_size)

    print(f"  Sweeping concepts {offset}–{offset + len(batch) - 1} of {total} "
          f"(batch {batch_num}/{total_batches}, cycle {state['cycle']})", file=sys.stderr)

    hits = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(check_concept, c): c for c in batch}
        for future in as_completed(futures):
            result = future.result()
            if result:
                hits.append(result)
    hits.sort(key=lambda h: h["ratio"], reverse=True)

    # Advance state
    next_offset = offset + args.batch_size
    if next_offset >= total:
        state["offset"] = 0
        state["cycle"]  = state.get("cycle", 1) + 1
        print(f"  Full sweep complete — starting cycle {state['cycle']}", file=sys.stderr)
    else:
        state["offset"] = next_offset
    state["last_run"] = datetime.now(timezone.utc).date().isoformat()
    save_state(state)

    print(f"  {len(hits)} signals in batch {batch_num}/{total_batches}", file=sys.stderr)

    items = []

    # Always emit a batch summary so the digest shows sweep progress
    if hits:
        top_names = ", ".join(h["name"] for h in hits[:3])
        summary_text = f"{len(hits)} signal{'s' if len(hits) != 1 else ''} found: {top_names}"
        if len(hits) > 3:
            summary_text += f" (+{len(hits) - 3} more)"
    else:
        summary_text = "No signals found"

    items.append({
        "title":        f"Early signal sweep — batch {batch_num}/{total_batches}",
        "summary":      f"{summary_text}. Scanned concepts {offset:,}–{offset + len(batch) - 1:,} of {total:,} (cycle {state['cycle'] - (1 if next_offset >= total else 0)}, threshold: ≥{MIN_PAPERS_2024} papers in 2024, {MIN_RATIO:.0f}–{MAX_RATIO:.0f}× growth since 2019).",
        "url":          "https://openalex.org/concepts",
        "source":       "OpenAlex Early Signal",
        "category":     "science",
        "engagement":   0.1,  # small non-zero so it doesn't get sorted out entirely
        "fetched_at":   now,
        "published_at": None,
    })

    # Individual items for each signal
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
