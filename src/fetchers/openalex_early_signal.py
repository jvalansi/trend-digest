#!/usr/bin/env python3
"""
OpenAlex early-signal fetcher — daily batch sweep of level-3 academic concepts.

Cycles through all ~24,749 level-3 concepts once per quarter (~65 working days).
Surfaces concepts with ≥200 papers in the most recent complete year and 5–50×
growth over the prior 5 years (e.g. 2024 vs 2019 when run in 2025).

Always emits a batch summary item (even when nothing found) so the digest shows
sweep progress. Individual signal items are emitted for each hit.

State file:    data/openalex_sweep_state.json
Concept cache: data/openalex_concepts_l3.json  (refreshed every 30 days)

Usage:
  python fetchers/openalex_early_signal.py [--batch-size N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import calendar
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

MIN_PAPERS_RECENT = 200
MIN_RATIO         = 5.0
MAX_RATIO         = 50.0   # above this is likely a bulk tag-reassignment artifact


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


def check_concept(concept: dict, recent_year: int, base_year: int) -> dict | None:
    cid = concept["id"]
    n_recent = count_papers(cid, recent_year)
    if n_recent < MIN_PAPERS_RECENT:
        return None
    n_base = count_papers(cid, base_year)
    if n_base < 0 or n_recent < 0:
        return None
    ratio = n_recent / max(n_base, 1)
    if ratio < MIN_RATIO or ratio > MAX_RATIO:
        return None
    return {"name": concept["name"], "id": concept["id"], "n_base": n_base, "n_recent": n_recent,
            "base_year": base_year, "recent_year": recent_year, "ratio": ratio}


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"offset": 0, "cycle": 1}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_quarter(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def quarter_working_days(d: date) -> int:
    q = (d.month - 1) // 3
    months = [q * 3 + 1, q * 3 + 2, q * 3 + 3]
    total = 0
    for m in months:
        _, days_in_month = calendar.monthrange(d.year, m)
        total += sum(1 for day in range(1, days_in_month + 1) if date(d.year, m, day).weekday() < 5)
    return total


def next_quarter_start(d: date) -> date:
    q = (d.month - 1) // 3
    if q == 3:
        return date(d.year + 1, 1, 1)
    return date(d.year, q * 3 + 4, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=0,
                        help="Concepts per run (default: 0 = auto, sized to fit the quarter)")
    args = parser.parse_args()

    concepts = load_or_refresh_concepts()
    state    = load_state()
    offset   = state["offset"]
    total    = len(concepts)

    now             = datetime.now(timezone.utc).isoformat()
    today           = date.today()
    current_quarter = get_quarter(today)
    cycle_quarter   = state.get("cycle_quarter", "")

    # Years: compare most recent complete year vs 5 years prior
    recent_year = today.year - 1
    base_year   = recent_year - 5

    # If the cycle just completed (offset reset to 0) and we're still in the same
    # quarter, wait — don't start the next cycle until the quarter rolls over.
    if offset == 0 and cycle_quarter == current_quarter:
        nq = next_quarter_start(today)
        nq_label = get_quarter(nq)
        print(f"  Sweep complete for {current_quarter} — waiting for {nq_label}", file=sys.stderr)
        items = [{
            "title":        f"Early signal sweep — waiting for {nq_label}",
            "summary":      f"This quarter's full sweep of {total:,} concepts is complete (cycle {state['cycle'] - 1}). Next sweep starts in {nq_label}.",
            "url":          "https://openalex.org/concepts",
            "source":       "OpenAlex Early Signal",
            "category":     "science",
            "engagement":   0.1,
            "fetched_at":   now,
            "published_at": None,
        }]
        print(json.dumps(items, ensure_ascii=False))
        return

    # Starting a new cycle (either first ever run, or the quarter has changed)
    if offset == 0:
        state["cycle_quarter"] = current_quarter
        if args.batch_size == 0:
            working_days = quarter_working_days(today)
            state["batch_size"] = math.ceil(total / working_days)
            print(f"  Auto batch size: {state['batch_size']} ({working_days} working days in {current_quarter})", file=sys.stderr)

    batch_size    = args.batch_size if args.batch_size > 0 else state.get("batch_size", math.ceil(total / 65))
    batch         = concepts[offset: offset + batch_size]
    batch_num     = offset // batch_size + 1
    total_batches = math.ceil(total / batch_size)

    print(f"  Sweeping concepts {offset}–{offset + len(batch) - 1} of {total} "
          f"(batch {batch_num}/{total_batches}, cycle {state['cycle']}, {base_year}→{recent_year})", file=sys.stderr)

    hits = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(check_concept, c, recent_year, base_year): c for c in batch}
        for future in as_completed(futures):
            result = future.result()
            if result:
                hits.append(result)
    hits.sort(key=lambda h: h["ratio"], reverse=True)

    # Advance state
    next_offset = offset + batch_size
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
        "summary":      f"{summary_text}. Scanned concepts {offset:,}–{offset + len(batch) - 1:,} of {total:,} (cycle {state['cycle'] - (1 if next_offset >= total else 0)}, threshold: ≥{MIN_PAPERS_RECENT} papers in {recent_year}, {MIN_RATIO:.0f}–{MAX_RATIO:.0f}× growth since {base_year}).",
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
            "summary":      f"{h['n_base']:,} → {h['n_recent']:,} papers ({h['base_year']}→{h['recent_year']}, {h['ratio']:.1f}× growth)",
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
