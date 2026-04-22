#!/usr/bin/env python3
"""
Running engagement stats using Welford's online algorithm.
Stores per-source mean/variance in stats.json, updated on each fetch.
"""

import json
import math
import os

STATS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "engagement_stats.json")

# TODO: historical z-scores (against running mean/variance) are a good signal —
# they'd let a story that's unusually viral for its source float higher.
# Consider blending: engagement = alpha * within_batch_z + (1-alpha) * historical_z


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


def _update_stats(source: str, raw_value: float) -> None:
    """Update running historical stats for source (Welford's algorithm)."""
    stats = _load()
    if source not in stats:
        stats[source] = {"n": 0, "mean": 0.0, "M2": 0.0}
    s = stats[source]
    s["n"] += 1
    delta = raw_value - s["mean"]
    s["mean"] += delta / s["n"]
    s["M2"] += delta * (raw_value - s["mean"])
    _save(stats)


def score_items(items: list[dict], source: str, raw_field: str) -> list[dict]:
    """Normalize engagement within the current batch (z-score), update historical stats."""
    drop_fields = {"score", "comments", "stars", "stars_today"} - {raw_field}

    raws = [float(item.get(raw_field, 0) or 0) for item in items]

    for raw in raws:
        _update_stats(source, raw)

    # Within-batch z-score so all sources compete on equal footing
    if len(raws) >= 2:
        mean = sum(raws) / len(raws)
        variance = sum((r - mean) ** 2 for r in raws) / (len(raws) - 1)
        std = math.sqrt(variance) if variance > 0 else 1.0
    else:
        mean, std = 0.0, 1.0

    for item, raw in zip(items, raws):
        z = (raw - mean) / std if std > 0 else 0.0
        item["engagement_raw"] = raw
        item["engagement"] = max(-3.0, min(3.0, round(z, 3)))
        for f in drop_fields:
            item.pop(f, None)
        item.pop(raw_field, None)

    return items
