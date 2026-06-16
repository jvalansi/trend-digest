#!/usr/bin/env python3
"""
OpenAlex early-signal fetcher — daily batch sweep of level-3 academic concepts.

Cycles through all ~24,749 level-3 concepts once per quarter, partitioned by
working day: on weekday N of the quarter, scans concepts[N*T/D : (N+1)*T/D]
where T = total concepts and D = working days in the quarter. Concepts are
sorted by ID so the partition is reproducible. No mutable state.

Surfaces concepts with ≥200 papers in the trailing 12 months and 5–50× growth
in *share of corpus* vs the same 12-month window 5 years prior. Normalizing
against global corpus growth (~2.8× over 5 years) removes the false positives
that raw-count thresholds produce for stagnant fields riding overall publication
inflation.

Always emits a batch summary item (even when nothing found) so the digest shows
sweep progress. Individual signal items are emitted for each hit.

Concept cache: data/openalex_concepts_l3.json  (refreshed every 30 days)

Usage:
  python fetchers/openalex_early_signal.py

Output: JSON array of normalized items to stdout.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timedelta, timezone

DATA_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
CONCEPTS_CACHE = os.path.join(DATA_DIR, "openalex_concepts_l3.json")

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


def count_papers(concept_id: str, from_date: date, to_date: date) -> int:
    params = urllib.parse.urlencode({
        "filter": f"concepts.id:{concept_id},type:article|preprint,from_publication_date:{from_date},to_publication_date:{to_date}",
        "per-page": 1,
        "select": "id",
        "mailto": MAILTO,
    })
    try:
        data = fetch_json(f"{BASE}/works?{params}")
        return int(data["meta"]["count"])
    except Exception:
        return -1


def count_corpus(from_date: date, to_date: date) -> int:
    params = urllib.parse.urlencode({
        "filter": f"type:article|preprint,from_publication_date:{from_date},to_publication_date:{to_date}",
        "per-page": 1,
        "select": "id",
        "mailto": MAILTO,
    })
    data = fetch_json(f"{BASE}/works?{params}")
    return int(data["meta"]["count"])


def check_concept(concept: dict, recent_from: date, recent_to: date,
                  base_from: date, base_to: date,
                  total_recent: int, total_base: int) -> dict | None:
    cid = concept["id"]
    n_recent = count_papers(cid, recent_from, recent_to)
    if n_recent < MIN_PAPERS_RECENT:
        return None
    n_base = count_papers(cid, base_from, base_to)
    if n_base < 0 or n_recent < 0:
        return None
    # Share of corpus: (n_recent/total_recent) / (n_base/total_base)
    # Equivalent to raw ratio divided by the global corpus-growth factor.
    share_recent = n_recent / total_recent
    share_base   = n_base   / total_base if n_base > 0 else 0.5 / total_base
    ratio        = share_recent / share_base
    raw_ratio    = n_recent / max(n_base, 1)
    if ratio < MIN_RATIO or ratio > MAX_RATIO:
        return None
    return {"name": concept["name"], "id": concept["id"],
            "n_base": n_base, "n_recent": n_recent,
            "recent_from": recent_from.isoformat(), "recent_to": recent_to.isoformat(),
            "base_from": base_from.isoformat(), "base_to": base_to.isoformat(),
            "ratio": ratio, "raw_ratio": raw_ratio}


def get_quarter(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def quarter_start(d: date) -> date:
    return date(d.year, ((d.month - 1) // 3) * 3 + 1, 1)


def quarter_end(d: date) -> date:
    q = (d.month - 1) // 3
    if q == 3:
        return date(d.year + 1, 1, 1) - timedelta(days=1)
    return date(d.year, q * 3 + 4, 1) - timedelta(days=1)


def working_days_in_range(start: date, end: date) -> int:
    """Count weekdays in [start, end] inclusive."""
    count = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            count += 1
        d += timedelta(days=1)
    return count


def main():
    concepts = load_or_refresh_concepts()
    concepts.sort(key=lambda c: c["id"])
    total = len(concepts)

    now             = datetime.now(timezone.utc).isoformat()
    today           = date.today()
    current_quarter = get_quarter(today)

    # Trailing 12 months ending yesterday, vs same window 5 years prior
    recent_to   = today - timedelta(days=1)
    recent_from = date(recent_to.year - 1, recent_to.month, recent_to.day)
    base_to     = date(recent_to.year - 5, recent_to.month, recent_to.day)
    base_from   = date(recent_from.year - 5, recent_from.month, recent_from.day)

    q_start    = quarter_start(today)
    q_end      = quarter_end(today)
    total_days = working_days_in_range(q_start, q_end)

    if today.weekday() >= 5:
        print(f"  Weekend — sweep paused for {current_quarter}", file=sys.stderr)
        items = [{
            "title":        f"Early signal sweep — paused (weekend)",
            "summary":      f"Sweep runs on weekdays only. {total:,} concepts partitioned across {total_days} working days of {current_quarter}.",
            "url":          "https://openalex.org/concepts",
            "source":       "OpenAlex Early Signal",
            "category":     "science",
            "engagement":   0.1,
            "fetched_at":   now,
            "published_at": None,
        }]
        print(json.dumps(items, ensure_ascii=False))
        return

    day_idx       = working_days_in_range(q_start, today) - 1
    start_concept = day_idx * total // total_days
    end_concept   = (day_idx + 1) * total // total_days
    batch         = concepts[start_concept:end_concept]

    print(f"  Sweeping concepts {start_concept}–{end_concept - 1} of {total} "
          f"(day {day_idx + 1}/{total_days} of {current_quarter}, "
          f"{base_from}–{base_to} vs {recent_from}–{recent_to})", file=sys.stderr)

    total_recent = count_corpus(recent_from, recent_to)
    total_base   = count_corpus(base_from,   base_to)
    corpus_growth = total_recent / total_base
    print(f"  Corpus: {total_base:,} → {total_recent:,} works ({corpus_growth:.2f}× growth)", file=sys.stderr)

    hits = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(check_concept, c, recent_from, recent_to, base_from, base_to,
                               total_recent, total_base): c for c in batch}
        for future in as_completed(futures):
            result = future.result()
            if result:
                hits.append(result)
    hits.sort(key=lambda h: h["ratio"], reverse=True)

    print(f"  {len(hits)} signals in day {day_idx + 1}/{total_days}", file=sys.stderr)

    items = []

    if hits:
        top_names = ", ".join(h["name"] for h in hits[:3])
        summary_text = f"{len(hits)} signal{'s' if len(hits) != 1 else ''} found: {top_names}"
        if len(hits) > 3:
            summary_text += f" (+{len(hits) - 3} more)"
    else:
        summary_text = "No signals found"

    items.append({
        "title":        f"Early signal sweep — day {day_idx + 1}/{total_days} of {current_quarter}",
        "summary":      f"{summary_text}. Scanned concepts {start_concept:,}–{end_concept - 1:,} of {total:,} (threshold: ≥{MIN_PAPERS_RECENT} papers in trailing 12 months, {MIN_RATIO:.0f}–{MAX_RATIO:.0f}× share-of-corpus growth vs same window 5 years prior; corpus grew {corpus_growth:.2f}×).",
        "url":          "https://openalex.org/concepts",
        "source":       "OpenAlex Early Signal",
        "category":     "science",
        "engagement":   0.1,
        "fetched_at":   now,
        "published_at": None,
    })

    # Individual items for each signal
    for h in hits:
        concept_slug = h["id"].split("/")[-1]
        items.append({
            "title":        h["name"],
            "summary":      f"{h['n_base']:,} → {h['n_recent']:,} papers ({h['base_from']}–{h['base_to']} vs {h['recent_from']}–{h['recent_to']}, {h['ratio']:.1f}× share, {h['raw_ratio']:.1f}× raw)",
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
