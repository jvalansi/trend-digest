#!/usr/bin/env python3
"""
Hugging Face trending models fetcher — pulls models sorted by trendingScore.

Usage:
  python fetchers/hf_models.py [--limit N]

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone

from stats import score_items

API_URL = "https://huggingface.co/api/models?sort=trendingScore&limit={limit}"

SKIP_TAGS = {"transformers", "safetensors", "region:us", "license:other", "license:apache-2.0",
             "license:mit", "eval-results", "endpoints_compatible", "has_space"}


def fetch_models(limit: int) -> list[dict]:
    url = API_URL.format(limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "trend-digest/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())

    items = []
    for model in data:
        model_id = model.get("id", "")
        pipeline = model.get("pipeline_tag", "")
        tags = [t for t in model.get("tags", []) if t not in SKIP_TAGS and not t.startswith("arxiv:")]
        summary_parts = [pipeline] + tags[:5]
        summary = ", ".join(p for p in summary_parts if p)
        items.append({
            "title": model_id,
            "summary": summary,
            "url": f"https://huggingface.co/{model_id}",
            "source": "HF Models",
            "category": "tech",
            "trending_score": model.get("trendingScore", 0) or 0,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": model.get("createdAt"),
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15, help="Number of models to fetch (default: 15)")
    args = parser.parse_args()

    print(f"  Fetching {args.limit} trending HF models...", file=sys.stderr)
    try:
        items = fetch_models(args.limit)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = score_items(items, "HF Models", "trending_score")
    items = sorted(items, key=lambda x: x["engagement"], reverse=True)
    print(f"  Got {len(items)} models", file=sys.stderr)
    print(json.dumps(items, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
