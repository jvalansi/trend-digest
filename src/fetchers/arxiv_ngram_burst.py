#!/usr/bin/env python3
"""
arXiv n-gram burst fetcher — surfaces emerging vocabulary across arXiv subject categories.

Cycles through all ~146 leaf categories from arxiv.org/category_taxonomy once per
quarter, partitioned by working day: on weekday N of the quarter, scans
categories[N*T/D : (N+1)*T/D] where T = total categories and D = working days in
the quarter. Categories are sorted alphabetically so the partition is reproducible.
No mutable state.

For each day's category slice, pulls titles + abstracts from a recent window and
a baseline window (default: same 90-day window 1 year prior), extracts 2- and
3-grams with content-word endpoints, and ranks by share-of-corpus growth:

    ratio = (n_recent / total_tokens_recent) / ((n_base + 1) / (total_tokens_base + 1))

The +1 smoothing keeps never-before-seen terms scorable (and bounds the ratio).

Filters: ≥MIN_RECENT_FREQ occurrences in recent window, content-word endpoints,
length 2–3, not in PHRASE_STOPLIST.

Always emits a sweep-progress summary item (even when nothing found) so the digest
shows where in the cycle we are. Individual burst terms are emitted as separate items.

Category cache: data/arxiv_categories.json  (refreshed every 30 days)

Usage:
  python fetchers/arxiv_ngram_burst.py
  python fetchers/arxiv_ngram_burst.py --categories cs.LG,cs.CL  # override rotation
  python fetchers/arxiv_ngram_burst.py --recent-from 2017-06-01 --recent-to 2017-08-31

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, date, timedelta, timezone
from xml.etree import ElementTree as ET

ARXIV_API      = "https://export.arxiv.org/api/query"
TAXONOMY_URL   = "https://arxiv.org/category_taxonomy"
DATA_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
CATEGORY_CACHE = os.path.join(DATA_DIR, "arxiv_categories.json")
PAGE_SIZE      = 1000
RATE_DELAY     = 3.0  # arXiv asks for ≥3 seconds between requests

MIN_RECENT_FREQ = 8    # lowered from 20 since per-day category slice is much smaller
MIN_RATIO       = 8.0
NGRAM_LENGTHS   = (2, 3)
TOP_N           = 10

CATEGORY_RE = re.compile(r"<h4>([a-zA-Z\-]+\.[a-zA-Z\-]+)\s*<span>\(([^)]+)\)</span></h4>")

# Endpoint stop-words: bigrams/trigrams may not start or end with these.
STOPWORDS = set("""
a an the and or but if then so as is are was were be been being have has had
do does did of in on at to for with by from about into through during without
this that these those it its their his her our we us they them you your
not no nor only just also too very much more most some any all every each
which what who when where why how
can could may might must will would should shall
new our both other another such same most one two three
use uses using used can also however thus therefore moreover furthermore
than rather either neither between among while across via
""".split())

# Phrase-level boilerplate to drop entirely.
PHRASE_STOPLIST = {
    "in this paper", "this paper", "we propose", "we present", "we show",
    "we demonstrate", "we introduce", "we provide", "we develop", "we study",
    "state of art", "our method", "our approach", "our model",
    "experimental results", "extensive experiments", "we evaluate",
    "we conduct", "show that", "shows that", "demonstrate that",
    "such as", "based on", "results show", "in particular",
    "ablations show", "ablation shows", "ablation studies",
    "llm agents increasingly", "agents increasingly rely",
    "increasingly rely on", "increasingly used",
    "distillation opd", "on-policy distillation opd",
    "study we propose", "study we present", "study we show",
    "study we develop", "study we introduce", "study we demonstrate",
    "paper we propose", "paper we present", "paper we show",
    "paper we introduce", "paper we develop", "paper we demonstrate",
    "similarity analysis", "feature selection", "natural images",
    "elemental composition",
}

TOKEN_RE = re.compile(r"[a-z][a-z0-9-]*")
YEAR_RE  = re.compile(r"(?:19|20)\d{2}")
ATOM_NS  = {"atom": "http://www.w3.org/2005/Atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/"}


def fetch_xml(url: str, max_retries: int = 6) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "trend-digest/1.0 (mailto:jvalansi1@gmail.com)",
    })
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == max_retries - 1:
                raise
            last_err = e
        except urllib.error.URLError as e:
            if attempt == max_retries - 1:
                raise
            last_err = e
        backoff = RATE_DELAY * (2 ** attempt)
        print(f"  arXiv API transient error ({last_err}); retrying in {backoff:.0f}s", file=sys.stderr)
        time.sleep(backoff)
    raise RuntimeError("unreachable")


def load_or_refresh_categories() -> list[dict]:
    if os.path.exists(CATEGORY_CACHE):
        age_days = (time.time() - os.path.getmtime(CATEGORY_CACHE)) / 86400
        if age_days < 30:
            with open(CATEGORY_CACHE) as f:
                cats = json.load(f)
            print(f"  Loaded {len(cats)} cached arXiv categories ({age_days:.0f}d old)", file=sys.stderr)
            return cats

    print(f"  Fetching arXiv category taxonomy from {TAXONOMY_URL}...", file=sys.stderr)
    req = urllib.request.Request(TAXONOMY_URL, headers={
        "User-Agent": "trend-digest/1.0 (mailto:jvalansi1@gmail.com)",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode()
    cats = [{"id": m.group(1), "name": m.group(2).strip()} for m in CATEGORY_RE.finditer(html)]
    if not cats:
        raise RuntimeError("Failed to parse any categories from arXiv taxonomy page")
    with open(CATEGORY_CACHE, "w") as f:
        json.dump(cats, f, indent=2)
    print(f"  Cached {len(cats)} arXiv categories", file=sys.stderr)
    return cats


def shift_years(d: date, years: int) -> date:
    """Subtract `years` from d, mapping Feb 29 to Feb 28 in non-leap target years."""
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return d.replace(year=d.year - years, day=28)


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
    count = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            count += 1
        d += timedelta(days=1)
    return count


def build_query(category: str, start_date: date, end_date: date) -> str:
    date_clause = (
        f"submittedDate:%5B{start_date.strftime('%Y%m%d')}0000+TO+"
        f"{end_date.strftime('%Y%m%d')}2359%5D"
    )
    return f"cat:{category}+AND+{date_clause}"


def fetch_category(category: str, start_date: date, end_date: date,
                   seen_ids: set[str]) -> list[str]:
    query = build_query(category, start_date, end_date)
    texts = []
    start = 0
    while True:
        url = (
            f"{ARXIV_API}?search_query={query}&start={start}&max_results={PAGE_SIZE}"
            f"&sortBy=submittedDate&sortOrder=ascending"
        )
        xml = fetch_xml(url)
        root = ET.fromstring(xml)
        entries = root.findall("atom:entry", ATOM_NS)
        if not entries:
            break
        for entry in entries:
            entry_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS) or ""
            if entry_id in seen_ids:
                continue
            seen_ids.add(entry_id)
            title   = entry.findtext("atom:title",   default="", namespaces=ATOM_NS) or ""
            summary = entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or ""
            texts.append(title + " " + summary)
        print(f"  ... {category}: {len(seen_ids):,} total abstracts ({start_date} → {end_date})",
              file=sys.stderr)
        if len(entries) < PAGE_SIZE:
            break
        start += PAGE_SIZE
        time.sleep(RATE_DELAY)
    return texts


def month_chunks(start_date: date, end_date: date) -> list[tuple[date, date]]:
    """Split [start_date, end_date] into ≤31-day chunks to keep each query under
    arXiv's ~10k deep-pagination ceiling."""
    chunks = []
    cur = start_date
    while cur <= end_date:
        nxt = min(cur + timedelta(days=30), end_date)
        chunks.append((cur, nxt))
        cur = nxt + timedelta(days=1)
    return chunks


def fetch_window(categories: list[str], start_date: date, end_date: date) -> list[str]:
    seen_ids: set[str] = set()
    texts: list[str] = []
    chunks = month_chunks(start_date, end_date)
    for category in categories:
        for chunk_start, chunk_end in chunks:
            texts.extend(fetch_category(category, chunk_start, chunk_end, seen_ids))
            time.sleep(RATE_DELAY)
    return texts


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def is_content_endpoint(token: str) -> bool:
    return token not in STOPWORDS and len(token) >= 3 and not token.isdigit()


def good_ngram(ngram: tuple[str, ...]) -> bool:
    if not is_content_endpoint(ngram[0]) or not is_content_endpoint(ngram[-1]):
        return False
    if any(YEAR_RE.search(tok) for tok in ngram):
        return False
    phrase = " ".join(ngram)
    if phrase in PHRASE_STOPLIST:
        return False
    # Reject trigrams whose inner bigrams are stoplisted (catches e.g.
    # "study we propose" via the "we propose" bigram).
    if len(ngram) == 3:
        if " ".join(ngram[:2]) in PHRASE_STOPLIST or " ".join(ngram[1:]) in PHRASE_STOPLIST:
            return False
    return True


def count_ngrams(texts: list[str]) -> tuple[Counter, int]:
    counter: Counter = Counter()
    total_tokens = 0
    for text in texts:
        tokens = tokenize(text)
        total_tokens += len(tokens)
        for n in NGRAM_LENGTHS:
            if len(tokens) < n:
                continue
            for i in range(len(tokens) - n + 1):
                ng = tuple(tokens[i:i+n])
                if good_ngram(ng):
                    counter[ng] += 1
    return counter, total_tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recent-from", help="ISO date for recent window start (default: 90 days ago)")
    parser.add_argument("--recent-to",   help="ISO date for recent window end (default: today)")
    parser.add_argument("--lookback-years", type=int, default=1)
    parser.add_argument("--categories", help="Comma-separated category override (default: today's slice of the quarterly rotation)")
    parser.add_argument("--top", type=int, default=TOP_N)
    parser.add_argument("--min-freq", type=int, default=MIN_RECENT_FREQ)
    parser.add_argument("--min-ratio", type=float, default=MIN_RATIO)
    args = parser.parse_args()

    today           = date.today()
    now             = datetime.now(timezone.utc).isoformat()
    current_quarter = get_quarter(today)
    recent_to   = date.fromisoformat(args.recent_to)   if args.recent_to   else today
    recent_from = date.fromisoformat(args.recent_from) if args.recent_from else recent_to - timedelta(days=90)
    base_to     = shift_years(recent_to,   args.lookback_years)
    base_from   = shift_years(recent_from, args.lookback_years)

    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
        day_idx = total_days = None
        slice_label = "+".join(categories)
        partition_note = f"manual override ({slice_label})"
    else:
        all_cats = sorted(load_or_refresh_categories(), key=lambda c: c["id"])
        total = len(all_cats)
        q_start    = quarter_start(today)
        q_end      = quarter_end(today)
        total_days = working_days_in_range(q_start, q_end)

        if today.weekday() >= 5:
            print(f"  Weekend — sweep paused for {current_quarter}", file=sys.stderr)
            items = [{
                "title":        "arXiv burst sweep — paused (weekend)",
                "summary":      f"Sweep runs on weekdays only. {total} arXiv categories partitioned across {total_days} working days of {current_quarter}.",
                "url":          "https://arxiv.org/category_taxonomy",
                "source":       "arXiv n-gram Burst",
                "category":     "science",
                "engagement":   0.1,
                "fetched_at":   now,
                "published_at": None,
            }]
            print(json.dumps(items, ensure_ascii=False))
            return

        day_idx   = working_days_in_range(q_start, today) - 1
        start_cat = day_idx * total // total_days
        end_cat   = (day_idx + 1) * total // total_days
        batch     = all_cats[start_cat:end_cat]
        categories = [c["id"] for c in batch]
        slice_label = ", ".join(categories) if categories else "(empty slice)"
        partition_note = (
            f"day {day_idx + 1}/{total_days} of {current_quarter}, "
            f"categories {start_cat}–{end_cat - 1} of {total}"
        )

    print(f"  Sweep: {partition_note}", file=sys.stderr)
    print(f"  Categories: {slice_label}", file=sys.stderr)
    print(f"  Recent:   {recent_from} → {recent_to}", file=sys.stderr)
    print(f"  Baseline: {base_from} → {base_to}", file=sys.stderr)

    recent_texts = fetch_window(categories, recent_from, recent_to) if categories else []
    base_texts   = fetch_window(categories, base_from,   base_to)   if categories else []

    print(f"  Tokenizing {len(recent_texts):,} recent + {len(base_texts):,} baseline abstracts",
          file=sys.stderr)
    recent_counts, recent_total = count_ngrams(recent_texts)
    base_counts,   base_total   = count_ngrams(base_texts)
    print(f"  {len(recent_counts):,} unique recent n-grams over {recent_total:,} tokens",
          file=sys.stderr)

    scored = []
    for ng, cnt in recent_counts.items():
        if cnt < args.min_freq:
            continue
        base_cnt     = base_counts.get(ng, 0)
        recent_share = cnt / recent_total
        base_share   = (base_cnt + 1) / (base_total + 1)
        ratio        = recent_share / base_share
        if ratio < args.min_ratio:
            continue
        scored.append((ng, cnt, base_cnt, ratio))

    scored.sort(key=lambda x: x[3], reverse=True)

    # Suppress lower-ranked variants that share a contiguous 2-token substring
    # with a higher-ranked term (e.g. "on-policy distillation opd" given
    # "on-policy distillation" already passed).
    def bigrams(ng: tuple[str, ...]) -> set[tuple[str, str]]:
        return {(ng[i], ng[i + 1]) for i in range(len(ng) - 1)}

    deduped: list = []
    kept_bigrams: set[tuple[str, str]] = set()
    for entry in scored:
        bg = bigrams(entry[0])
        if bg & kept_bigrams:
            continue
        deduped.append(entry)
        kept_bigrams |= bg

    top = deduped[:args.top]
    print(f"  {len(scored)} terms passing thresholds, {len(deduped)} after dedup; surfacing top {len(top)}", file=sys.stderr)

    if day_idx is not None:
        header_title = f"arXiv burst sweep — day {day_idx + 1}/{total_days} of {current_quarter}"
    else:
        header_title = f"arXiv burst sweep — {slice_label}"

    items = [{
        "title":        header_title,
        "summary":      (
            f"Scanned {slice_label}. "
            f"{len(top)} emerging term{'s' if len(top) != 1 else ''} in "
            f"{len(recent_texts):,} recent abstracts ({recent_from}→{recent_to}) vs "
            f"{len(base_texts):,} baseline ({base_from}→{base_to}). "
            f"Threshold: ≥{args.min_freq} occurrences, ≥{args.min_ratio:.0f}× share growth."
        ),
        "url":          (
            f"https://arxiv.org/list/{categories[0]}/recent"
            if categories else "https://arxiv.org/category_taxonomy"
        ),
        "source":       "arXiv n-gram Burst",
        "category":     "science",
        "engagement":   0.1,
        "fetched_at":   now,
        "published_at": None,
    }]

    for ng, cnt, base_cnt, ratio in top:
        phrase = " ".join(ng)
        items.append({
            "title":        phrase,
            "summary":      (
                f"{cnt:,} mentions in {recent_from}→{recent_to} vs {base_cnt:,} in "
                f"{base_from}→{base_to} ({ratio:.1f}× share growth)"
            ),
            "url":          f"https://arxiv.org/search/?searchtype=all&query={urllib.parse.quote(phrase)}",
            "source":       "arXiv n-gram Burst",
            "category":     "science",
            "engagement":   round(min(ratio, 100), 2),
            "fetched_at":   now,
            "published_at": None,
        })

    print(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()
