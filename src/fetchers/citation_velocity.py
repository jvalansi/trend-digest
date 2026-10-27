#!/usr/bin/env python3
"""
Citation velocity — rank papers by citations gained recently, not by total.

Total citations make the same well-cited papers win every day. This keeps a
small per-source history of citation counts in data/citation_history.json and
scores each paper by citations gained per WINDOW_DAYS, measured over the last
WINDOW_DAYS (or since first seen, if newer). Papers tracked for under MIN_DAYS
have no gain yet, so a new source's section stays empty for its first days.
"""

import json
import os
from datetime import date, timedelta

from stats import score_items

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "citation_history.json")
WINDOW_DAYS = 7
MIN_DAYS = 3  # shorter spans are too noisy to scale up to a weekly rate
KEEP_DAYS = WINDOW_DAYS + 7


def _load() -> dict:
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(history: dict) -> None:
    tmp = HISTORY_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(history, f)
    os.replace(tmp, HISTORY_FILE)


def record_gains(source: str, counts: dict[str, int], history: dict, today: date) -> dict[str, float]:
    """Add today's counts to `history[source]` and return each id's citations per
    WINDOW_DAYS, measured from the newest snapshot at or before the window start
    (else the oldest one). Ids tracked for under MIN_DAYS get 0. Prunes snapshots
    older than KEEP_DAYS."""
    snaps = history.setdefault(source, {})
    window_start = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    gains = {}
    for pid, count in counts.items():
        s = snaps.setdefault(pid, {})
        s[today.isoformat()] = count
        before = [d for d in s if d <= window_start]
        base = max(before) if before else min(s)
        elapsed = (today - date.fromisoformat(base)).days
        gains[pid] = (count - s[base]) * WINDOW_DAYS / elapsed if elapsed >= MIN_DAYS else 0.0
    for pid in list(snaps):
        snaps[pid] = {d: c for d, c in snaps[pid].items() if d >= cutoff}
        if not snaps[pid]:
            del snaps[pid]
    return gains


def rank_by_gain(items: list[dict], source: str, key_field: str, count_field: str) -> list[dict]:
    """Record today's counts, keep items that gained citations, and z-score them on
    their weekly gain. `key_field` must be a stable paper id."""
    history = _load()
    gains = record_gains(source, {i[key_field]: i[count_field] for i in items}, history, date.today())
    _save(history)
    rising = [dict(i, gain=round(gains[i[key_field]], 1)) for i in items if gains[i[key_field]] > 0]
    for i in rising:
        i.pop(key_field, None)
        i.pop(count_field, None)
    return score_items(rising, source, "gain", f"citations/{WINDOW_DAYS}d")
