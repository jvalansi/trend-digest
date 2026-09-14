"""Fetch-failure tolerance in the arXiv n-gram burst sweep.

Run: python src/fetchers/test_arxiv_ngram_burst.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fetchers import arxiv_ngram_burst as m

m.time.sleep = lambda *_: None

WINDOW = (date(2026, 6, 16), date(2026, 9, 14))


def fake_fetch(category, start_date, end_date):
    if category == "cs.LG":
        raise RuntimeError("HTTP Error 429: Too Many Requests")
    # 1234 is cross-listed in cs.AI and math.ST.
    return [(f"{category}:{start_date}", f"{category} abstract"),
            ("http://arxiv.org/abs/1234", "shared abstract")]


m.fetch_category = fake_fetch
per_cat, failed = m.fetch_window(["cs.AI", "cs.LG", "math.ST"], *WINDOW)

assert failed == {"cs.LG"}, failed
assert set(per_cat) == {"cs.AI", "math.ST"}, per_cat
# 3 month-chunks over a 90-day window, 2 entries each.
assert len(per_cat["cs.AI"]) == 6, len(per_cat["cs.AI"])

texts = m.pool_texts(per_cat, [c for c in ["cs.AI", "cs.LG", "math.ST"] if c not in failed])
# 3 unique per surviving category + 1 shared paper counted once.
assert len(texts) == 7, len(texts)
assert texts.count("shared abstract") == 1, texts

print("ok")
