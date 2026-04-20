#!/usr/bin/env python3
"""
Running engagement stats using Welford's online algorithm.
Stores per-source mean/variance in stats.json, updated on each fetch.
"""

import json
import math
import os

STATS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "engagement_stats.json")


def _load() -> dict:
    try:
        with open(STATS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(stats: dict) -> None:
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def update_and_score(source: str, raw_value: float) -> float:
    """Update running stats for source and return normalized z-score clamped to [-3, 3]."""
    stats = _load()

    if source not in stats:
        stats[source] = {"n": 0, "mean": 0.0, "M2": 0.0}

    s = stats[source]
    s["n"] += 1
    delta = raw_value - s["mean"]
    s["mean"] += delta / s["n"]
    delta2 = raw_value - s["mean"]
    s["M2"] += delta * delta2

    _save(stats)

    if s["n"] < 2:
        return 0.0

    variance = s["M2"] / (s["n"] - 1)
    std = math.sqrt(variance) if variance > 0 else 1.0
    z = (raw_value - s["mean"]) / std
    return max(-3.0, min(3.0, round(z, 3)))


def score_items(items: list[dict], source: str, raw_field: str) -> list[dict]:
    """Add raw and normalized engagement scores to each item."""
    drop_fields = {"score", "comments", "stars", "stars_today"} - {raw_field}
    for item in items:
        raw = item.get(raw_field, 0) or 0
        item["engagement_raw"] = float(raw)
        item["engagement"] = update_and_score(source, float(raw))
        for f in drop_fields:
            item.pop(f, None)
        item.pop(raw_field, None)
    return items
