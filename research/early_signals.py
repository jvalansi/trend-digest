#!/usr/bin/env python3
"""
Track early signals for major science clusters by counting publications per year.
- OpenAlex API for CS/physics/ML clusters (free, 10 req/sec, no auth needed)
- PubMed E-utilities for biomedical clusters

Output: data/early_signals.csv
  cluster, year, papers, source
"""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

OUTPUT = "/home/ubuntu/trend-digest/data/early_signals.csv"
START_YEAR = 2000
END_YEAR   = 2024

# Each cluster: (name, source, query)
# openalex_concept: filter by OpenAlex concept ID (most precise — citation-derived field boundaries)
# openalex_kw: keyword search in title+abstract (fallback for fields without a concept ID)
# pubmed: PubMed keyword search (better coverage for clinical/biomedical literature)
CLUSTERS = [
    # CS / AI — OpenAlex concept IDs
    ("deep_learning",         "openalex_concept", "C108583219"),           # Deep learning
    ("language_model_llm",    "openalex_concept", "C137293760"),           # Language model (covers transformers, LLMs)
    ("gpu_computing",         "openalex_concept", "C50630238"),            # GPGPU
    ("robotic_surgery",       "openalex_concept", "C103203806"),           # Robotic surgery
    ("chip_eda",              "openalex_concept", "C64260653"),            # Electronic design automation
    ("euv_lithography",       "openalex_concept", "C162996421"),           # Extreme ultraviolet lithography

    # No clean concept ID — use keyword fallback
    ("diffusion_models",      "openalex_kw",      "diffusion model score matching denoising generative"),

    # Biomedical — OpenAlex concept IDs
    ("glp1_agonists",         "openalex_concept", "C2776398474"),          # Glucagon-like peptide-1
    ("immune_checkpoint",     "openalex_concept", "C2780851360"),          # Immune checkpoint
    ("crispr",                "openalex_concept", "C98108389"),            # CRISPR
    ("car_t_cell",            "openalex_concept", "C2911194787"),          # CAR T-cell therapy
    ("aav_gene_therapy",      "openalex_concept", "C2778107364"),          # Adeno-associated virus
    ("cftr_modulators",       "openalex_concept", "C2778428886"),          # CFTR
    ("continuous_glucose",    "openalex_concept", "C2986379492"),          # Continuous glucose monitoring
    ("protein_structure_pred","openalex_concept", "C18051474"),            # Protein structure prediction
    ("antibody_drug_conj",    "openalex_concept", "C2777325958"),          # Antibody-drug conjugate

    # mRNA therapeutics — no single concept; use PubMed for clinical specificity
    ("mrna_therapeutics",     "pubmed", "mRNA vaccine OR mRNA therapy OR lipid nanoparticle mRNA"),
]


def openalex_fetch(filter_str: str, year: int) -> int:
    """Count papers in OpenAlex using an arbitrary filter string."""
    params = {
        "filter": f"{filter_str},publication_year:{year}",
        "per_page": 1,
        "select": "id",
        "mailto": "jvalansi1@gmail.com",
    }
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "research/1.0 (jvalansi1@gmail.com)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return int(data["meta"]["count"])
    except Exception as e:
        print(f"    WARN OpenAlex {year}: {e}", file=sys.stderr)
        return -1


def openalex_count_concept(concept_id: str, year: int) -> int:
    return openalex_fetch(f"concepts.id:{concept_id}", year)


def openalex_count_kw(query: str, year: int) -> int:
    return openalex_fetch(f"title_and_abstract.search:{urllib.parse.quote(query)}", year)


def pubmed_count_year(query: str, year: int) -> int:
    """Count PubMed papers matching query in a given year."""
    full_query = f"({query}) AND {year}[pdat]"
    params = {
        "db": "pubmed",
        "term": full_query,
        "rettype": "count",
        "retmode": "json",
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "research/1.0 (jvalansi1@gmail.com)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return int(data["esearchresult"]["count"])
    except Exception as e:
        print(f"    WARN PubMed {year}: {e}", file=sys.stderr)
        return -1


def _linfit(xs: list, ys: list) -> tuple[float, float]:
    """Return (slope, intercept) for least-squares line through (xs, ys)."""
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0.0, sy / n
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def _sse(xs: list, ys: list, slope: float, intercept: float) -> float:
    return sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))


def find_breakpoint(year_counts: dict, min_peak: int = 50, min_slope_ratio: float = 1.1,
                    min_level_shift: float = 0.7) -> int | None:
    """
    Find the year where publication growth structurally accelerated.

    Fits two log-linear segments (before/after each candidate breakpoint) and
    picks the split that minimizes total SSE.  Reports a breakpoint if either:
      (a) slope-change: post-slope >= min_slope_ratio × pre-slope (slope sped up)
      (b) level-shift:  log-count at breakpoint jumped >= min_level_shift above the
          left segment's prediction at that point (sudden step-up even if slope unchanged)

    min_level_shift=0.7 ≈ 2× in actual paper count.
    """
    import math
    years = sorted(year_counts)
    if len(years) < 8:
        return None
    if max(year_counts.values()) < min_peak:
        return None

    log_counts = [math.log(max(year_counts[y], 0.5)) for y in years]
    xs = list(range(len(years)))

    best_sse = float("inf")
    best_bp = None
    best_slopes = (0.0, 0.0)
    best_intercepts = (0.0, 0.0)

    for bp in range(3, len(years) - 3):
        s_l, i_l = _linfit(xs[:bp], log_counts[:bp])
        s_r, i_r = _linfit(xs[bp:], log_counts[bp:])
        sse = _sse(xs[:bp], log_counts[:bp], s_l, i_l) + _sse(xs[bp:], log_counts[bp:], s_r, i_r)
        if sse < best_sse:
            best_sse = sse
            best_bp = bp
            best_slopes = (s_l, s_r)
            best_intercepts = (i_l, i_r)

    s_pre, s_post = best_slopes
    i_pre, i_post = best_intercepts
    bp_x = best_bp

    # Condition (a): slope acceleration
    slope_accel = s_post > 0 and (s_pre <= 0 or s_post >= s_pre * min_slope_ratio)

    # Condition (b): level-shift — right segment's value at breakpoint exceeds left segment's prediction
    left_pred = s_pre * bp_x + i_pre
    right_val  = s_post * bp_x + i_post
    level_shift = (right_val - left_pred) >= min_level_shift

    if slope_accel or level_shift:
        return years[best_bp]
    return None


def main():
    import os
    years = list(range(START_YEAR, END_YEAR + 1))

    # Load existing rows (e.g. PubMed data already fetched)
    existing_rows = []
    existing_keys = set()
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            for r in csv.DictReader(f):
                existing_rows.append(r)
                existing_keys.add((r["cluster"], int(r["year"])))
        print(f"Loaded {len(existing_rows)} existing rows from {OUTPUT}", file=sys.stderr)

    rows = list(existing_rows)

    for cluster_name, source, query in CLUSTERS:
        print(f"\n[{cluster_name}] source={source}", file=sys.stderr)
        # Skip if all years already fetched
        already = sum(1 for y in years if (cluster_name, y) in existing_keys)
        if already == len(years):
            print(f"  (already complete, skipping)", file=sys.stderr)
            continue

        counts = []
        for year in years:
            if (cluster_name, year) in existing_keys:
                counts.append(None)
                continue
            if source == "openalex_concept":
                count = openalex_count_concept(query, year)
                time.sleep(0.15)
            elif source == "openalex_kw":
                count = openalex_count_kw(query, year)
                time.sleep(0.15)
            else:
                count = pubmed_count_year(query, year)
                time.sleep(0.34)
            counts.append(count)
            if count >= 0:
                print(f"  {year}: {count:,}", file=sys.stderr)

        for year, count in zip(years, counts):
            if count is not None and count >= 0:
                rows.append({
                    "cluster": cluster_name,
                    "year": year,
                    "papers": count,
                    "source": source,
                })

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cluster", "year", "papers", "source"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT}", file=sys.stderr)

    cluster_data = defaultdict(dict)
    for r in rows:
        cluster_data[r["cluster"]][int(r["year"])] = int(r["papers"])

    print("\n=== ACCELERATION YEARS (piecewise log-linear breakpoint) ===", file=sys.stderr)
    for cluster, year_counts in sorted(cluster_data.items()):
        accel_year = find_breakpoint(year_counts)
        peak_year = max(year_counts, key=lambda y: year_counts[y])
        peak_count = year_counts[peak_year]
        print(f"  {cluster:<30} accel={accel_year}  peak={peak_year} ({peak_count:,} papers)", file=sys.stderr)


if __name__ == "__main__":
    main()
