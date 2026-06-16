#!/usr/bin/env python3
"""
arXiv n-gram burst fetcher — surfaces emerging vocabulary in ML/CS/AI abstracts.

Pulls titles + abstracts from a recent window and a baseline window (default: same
window 1 year prior), extracts 2- and 3-grams with content-word endpoints, and
ranks by share-of-corpus growth:

    ratio = (n_recent / total_tokens_recent) / ((n_base + 1) / (total_tokens_base + 1))

The +1 smoothing keeps never-before-seen terms scorable (and bounds the ratio).

Filters: ≥MIN_RECENT_FREQ occurrences in recent window, content-word endpoints,
length 2–3, not in PHRASE_STOPLIST.

Usage:
  python fetchers/arxiv_ngram_burst.py
  python fetchers/arxiv_ngram_burst.py --recent-from 2017-06-01 --recent-to 2017-08-31

Output: JSON array of normalized items to stdout.
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, date, timedelta, timezone
from xml.etree import ElementTree as ET

ARXIV_API   = "https://export.arxiv.org/api/query"
PAGE_SIZE   = 1000
RATE_DELAY  = 3.0  # arXiv asks for ≥3 seconds between requests

MIN_RECENT_FREQ = 20
MIN_RATIO       = 5.0
NGRAM_LENGTHS   = (2, 3)
TOP_N           = 20

DEFAULT_CATEGORIES = ["cs.LG", "cs.CL", "cs.AI", "cs.CV"]

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
    return phrase not in PHRASE_STOPLIST


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
    parser.add_argument("--categories", default=",".join(DEFAULT_CATEGORIES))
    parser.add_argument("--top", type=int, default=TOP_N)
    parser.add_argument("--min-freq", type=int, default=MIN_RECENT_FREQ)
    parser.add_argument("--min-ratio", type=float, default=MIN_RATIO)
    args = parser.parse_args()

    categories = [c.strip() for c in args.categories.split(",")]
    today      = date.today()
    recent_to   = date.fromisoformat(args.recent_to)   if args.recent_to   else today
    recent_from = date.fromisoformat(args.recent_from) if args.recent_from else recent_to - timedelta(days=90)
    base_to     = date(recent_to.year   - args.lookback_years, recent_to.month,   recent_to.day)
    base_from   = date(recent_from.year - args.lookback_years, recent_from.month, recent_from.day)
    now         = datetime.now(timezone.utc).isoformat()

    print(f"  Fetching arXiv {categories}", file=sys.stderr)
    print(f"  Recent:   {recent_from} → {recent_to}", file=sys.stderr)
    print(f"  Baseline: {base_from} → {base_to}", file=sys.stderr)

    recent_texts = fetch_window(categories, recent_from, recent_to)
    base_texts   = fetch_window(categories, base_from,   base_to)

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
    top = scored[:args.top]
    print(f"  {len(scored)} terms passing thresholds; surfacing top {len(top)}", file=sys.stderr)

    cat_label = "+".join(categories)
    items = [{
        "title":        f"arXiv burst sweep — {cat_label}",
        "summary":      (
            f"{len(top)} emerging term{'s' if len(top) != 1 else ''} in "
            f"{len(recent_texts):,} recent abstracts ({recent_from}→{recent_to}) vs "
            f"{len(base_texts):,} baseline ({base_from}→{base_to}). "
            f"Threshold: ≥{args.min_freq} occurrences, ≥{args.min_ratio:.0f}× share growth."
        ),
        "url":          f"https://arxiv.org/list/{categories[0]}/recent",
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
