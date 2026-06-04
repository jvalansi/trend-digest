#!/usr/bin/env python3
"""
Identify major science breakthroughs by mainstream impact.

Pipeline:
  1. Pull monthly Wikipedia top-1000 articles for 2015–2025
  2. Deduplicate → unique articles with per-month view counts
  3. Filter to science-related articles via Wikipedia categories
  4. Compute spike ratio (peak / median baseline) per article
  5. Query Google Trends for top spike articles → comparable peak score
  6. Output CSV ranked by Google Trends peak

Usage:
  python research/science_breakthroughs.py [--top N] [--out FILE]
"""

import argparse
import csv
import json
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# --- Config ---

WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

# Phrases in the article description that indicate it's a person, sport, or politics article.
DESC_EXCLUDE_PATTERNS = [
    # people (descriptions often start with nationality + profession)
    r"\b(politician|president|prime minister|senator|governor|monarch|king|queen|prince|princess)\b",
    r"\b(actor|actress|musician|singer|rapper|composer|director|filmmaker)\b",
    r"\b(footballer|basketball player|tennis player|athlete|olympian|cricketer)\b",
    r"\b(criminal|murderer|serial killer|convicted|drug lord|drug trafficker|drug trafficking|drug cartel|narco)\b",
    r"\b(justice|judge|lawyer|attorney)\b",
    r"\b(journalist|reporter|commentator|pundit|podcaster)\b",
    r"\b(businessman|businesswoman|entrepreneur|CEO|executive)\b",
    r"\b(author|writer|novelist|poet)\b",
    # events
    r"\b(edition of|world cup|olympic games|championship|tournament|league season)\b",
    r"\b(election|referendum|presidential|parliamentary)\b",
    r"\b(film|movie|television series|TV series|album|song|video game)\b",
    r"\b(disaster|massacre|attack|shooting|bombing|incident)\b",
    # ideologies / other
    r"\b(conspiracy theory|political movement|ideolog)\b",
    r"\b(aztec|mesoamerican|indigenous|mythology|mytholog|ancient)\b",
    r"\b(treaty|agreement|accord|pact|convention)\b",
]

# Phrases in the article description that indicate it IS a science/health/technology topic.
DESC_POSITIVE_PATTERNS = [
    r"\b(disease|disorder|syndrome|infection|virus|bacteria|pathogen|pandemic|epidemic)\b",
    r"\b(vaccine|vaccination|antiviral|antibiotic|immunotherapy)\b",
    r"\b(drug|medication|pharmaceutical|therapy|treatment|clinical)\b",
    r"\b(gene|genome|dna|rna|protein|enzyme|chromosome|cell|organism)\b",
    r"\b(cancer|tumor|carcinoma|oncology|leukemia|lymphoma)\b",
    r"\b(biology|chemistry|physics|neuroscience|astronomy|genetics|ecology|mathematics)\b",
    r"\b(biochemistry|molecular|immunology|virology|pharmacology|epidemiology)\b",
    r"\b(genomics|biotechnology|nanotechnology|microbiology|physiology)\b",
    r"\b(astrophysics|quantum|particle physics|nuclear|radioactive|isotope|astronomical|gravitational)\b",
    r"\b(artificial intelligence|\bAI\b|machine learning|deep learning|neural network|large language model|chatbot|generative)\b",
    r"\b(spacecraft|space probe|telescope|exoplanet|black hole|asteroid|comet|space mission|nasa|space agency)\b",
    r"\b(scientific discovery|scientific experiment|scientific research|scientific study)\b",
    r"\b(climate change|global warming|greenhouse gas|carbon dioxide)\b",
    r"\b(evolution|species|taxonomy|extinction|fossil)\b",
]

WIKIPEDIA_TOP_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{year}/{month:02d}/all-days"

SKIP_PREFIXES = ("Special:", "Wikipedia:", "Help:", "Portal:", "File:", "Template:", "Talk:")
SKIP_STARTS = ("Deaths_in", "List_of", "Index_of", "Outline_of")


def ua_request(url: str, timeout: int = 15, retries: int = 4) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "research/1.0 (jvalansi1@gmail.com)"})
    delay = 2.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError(f"Failed after {retries} attempts: {url}")


# Step 1: Pull monthly top-1000 (sequential with small delay to avoid 429)
def fetch_month(year: int, month: int) -> list[tuple[str, int]]:
    url = WIKIPEDIA_TOP_URL.format(year=year, month=month)
    try:
        data = json.loads(ua_request(url))
        articles = data["items"][0]["articles"]
        result = []
        for art in articles:
            title = art["article"]
            if any(title.startswith(p) for p in SKIP_PREFIXES):
                continue
            if any(title.startswith(s) for s in SKIP_STARTS):
                continue
            result.append((title, art["views"]))
        return result
    except Exception as e:
        print(f"  WARN {year}-{month:02d}: {e}", file=sys.stderr)
        return []


def collect_all_months(start_year=2015, start_month=7) -> dict[str, dict[str, int]]:
    """Returns {article: {YYYY-MM: views}}"""
    now = datetime.now(timezone.utc)
    months = []
    y, m = start_year, start_month
    while (y, m) <= (now.year, now.month - 1):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    print(f"Fetching {len(months)} months of Wikipedia top-1000 (sequential)...", file=sys.stderr)
    article_views: dict[str, dict[str, int]] = defaultdict(dict)

    for i, (y, m) in enumerate(months):
        key = f"{y}-{m:02d}"
        results = fetch_month(y, m)
        for title, views in results:
            article_views[title][key] = views
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(months)} months, {len(article_views)} unique articles", file=sys.stderr)
        time.sleep(0.3)  # gentle pacing

    print(f"Total unique articles: {len(article_views)}", file=sys.stderr)
    return dict(article_views)


# Step 2: Score articles — combine spike ratio and peak absolute views
def compute_scores(article_views: dict[str, dict[str, int]], min_months: int = 1) -> list[dict]:
    results = []
    all_peaks = []
    for title, monthly in article_views.items():
        if len(monthly) < min_months:
            continue
        views_list = list(monthly.values())
        peak_views = max(views_list)
        all_peaks.append(peak_views)

    if not all_peaks:
        return []

    peak_p95 = sorted(all_peaks)[int(len(all_peaks) * 0.95)]

    for title, monthly in article_views.items():
        if len(monthly) < min_months:
            continue
        views_list = list(monthly.values())
        peak_views = max(views_list)
        peak_month = max(monthly, key=lambda k: monthly[k])
        others = [v for k, v in monthly.items() if k != peak_month]
        baseline = statistics.median(others) if len(others) >= 2 else (others[0] if others else 1)
        spike_ratio = peak_views / max(baseline, 1)
        # Combined score: normalized peak + spike ratio
        peak_norm = peak_views / peak_p95
        combined = peak_norm * 0.5 + min(spike_ratio / 10, 1.0) * 0.5
        results.append({
            "title": title,
            "peak_month": peak_month,
            "peak_views": peak_views,
            "baseline_views": round(baseline),
            "spike_ratio": round(spike_ratio, 2),
            "months_seen": len(monthly),
            "combined_score": round(combined, 4),
        })
    return sorted(results, key=lambda x: x["combined_score"], reverse=True)


# Step 3: Description-based science filter
def get_description(title: str) -> str:
    url = WIKIPEDIA_SUMMARY_URL.format(title=urllib.parse.quote(title, safe=""))
    try:
        data = json.loads(ua_request(url, timeout=10, retries=3))
        return (data.get("description") or "").lower()
    except Exception:
        return ""


def is_science(description: str) -> bool:
    for pattern in DESC_EXCLUDE_PATTERNS:
        if re.search(pattern, description, re.IGNORECASE):
            return False
    for pattern in DESC_POSITIVE_PATTERNS:
        if re.search(pattern, description, re.IGNORECASE):
            return True
    return False


def filter_science(scores: list[dict], top_n: int = 500) -> list[dict]:
    candidates = scores[:top_n]
    print(f"Checking descriptions for top {len(candidates)} articles (5 workers)...", file=sys.stderr)

    science_items = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(get_description, item["title"]): item for item in candidates}
        done = 0
        for future in as_completed(futures):
            item = futures[future]
            desc = future.result()
            if is_science(desc):
                item["description"] = desc
                science_items.append(item)
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(candidates)} checked, {len(science_items)} science so far", file=sys.stderr)

    print(f"Science articles: {len(science_items)}", file=sys.stderr)
    return sorted(science_items, key=lambda x: x["combined_score"], reverse=True)


# Step 4: Google Trends
def query_google_trends(titles: list[str], batch_size: int = 5) -> dict[str, int]:
    from pytrends.request import TrendReq

    pytrends = TrendReq(hl="en-US", tz=0, timeout=(10, 25), retries=2, backoff_factor=1.0)
    scores = {}

    for i in range(0, len(titles), batch_size):
        batch = titles[i:i + batch_size]
        display = [t.replace("_", " ") for t in batch]
        try:
            pytrends.build_payload(display, timeframe="2015-01-01 2025-12-31", geo="")
            df = pytrends.interest_over_time()
            if df is not None and not df.empty:
                for col in df.columns:
                    if col == "isPartial":
                        continue
                    orig = next((t for t in batch if t.replace("_", " ") == col), col)
                    scores[orig] = int(df[col].max())
            print(f"  Trends batch {i//batch_size + 1}: {list(scores.keys())[-len(batch):]}", file=sys.stderr)
        except Exception as e:
            print(f"  WARN trends batch {i}: {e}", file=sys.stderr)
        time.sleep(2.0)

    return scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=500, help="Top N articles to category-check (default: 500)")
    parser.add_argument("--trends-top", type=int, default=60, help="Top N science articles for Google Trends (default: 60)")
    parser.add_argument("--out", default="/home/ubuntu/trend-digest/data/science_breakthroughs.csv")
    parser.add_argument("--skip-trends", action="store_true", help="Skip Google Trends step")
    parser.add_argument("--cache", default="/home/ubuntu/trend-digest/data/wiki_article_views.json")
    args = parser.parse_args()

    import os
    if os.path.exists(args.cache):
        print(f"Loading from cache: {args.cache}", file=sys.stderr)
        with open(args.cache) as f:
            article_views = json.load(f)
        print(f"Loaded {len(article_views)} unique articles", file=sys.stderr)
    else:
        article_views = collect_all_months()
        with open(args.cache, "w") as f:
            json.dump(article_views, f)
        print(f"Cached to {args.cache}", file=sys.stderr)

    print("Computing scores...", file=sys.stderr)
    scored = compute_scores(article_views)
    print(f"Top 5 overall: {[x['title'] for x in scored[:5]]}", file=sys.stderr)

    science = filter_science(scored, top_n=args.top)

    trends_scores = {}
    if not args.skip_trends and science:
        top_titles = [item["title"] for item in science[:args.trends_top]]
        print(f"Querying Google Trends for {len(top_titles)} articles...", file=sys.stderr)
        trends_scores = query_google_trends(top_titles)

    for item in science:
        item["trends_peak"] = trends_scores.get(item["title"], "")

    # Deduplicate: if multiple articles share the same peak_month and description keywords,
    # keep only the one with the highest peak_views.
    seen_peaks: dict[str, dict] = {}
    for item in sorted(science, key=lambda x: x["peak_views"], reverse=True):
        key = item["peak_month"][:7]  # YYYY-MM
        desc_words = frozenset(item["description"].split()[:4])
        # Check if any existing entry for this month has similar description
        duplicate = False
        for k, existing in seen_peaks.items():
            if k.startswith(key) and len(desc_words & frozenset(existing["description"].split()[:4])) >= 2:
                duplicate = True
                break
        if not duplicate:
            seen_peaks[f"{key}_{item['title']}"] = item

    final = sorted(seen_peaks.values(), key=lambda x: (x.get("trends_peak") or 0), reverse=True)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "title", "peak_month", "peak_views", "baseline_views",
            "spike_ratio", "combined_score", "months_seen", "trends_peak", "description"
        ])
        writer.writeheader()
        for item in final:
            writer.writerow(item)

    print(f"\nWrote {len(final)} rows to {args.out}", file=sys.stderr)
    print("\nTop 30 by combined score:", file=sys.stderr)
    for item in sorted(science, key=lambda x: x["combined_score"], reverse=True)[:30]:
        tp = item.get("trends_peak", "")
        print(f"  trends={str(tp):>3}  spike={item['spike_ratio']:>6}x  peak={item['peak_views']:>10,}  {item['peak_month']}  {item['title']}", file=sys.stderr)


if __name__ == "__main__":
    main()
