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

# Each cluster: (name, source, search_query)
# OpenAlex: title/abstract keyword search
# PubMed: standard MeSH/keyword search
CLUSTERS = [
    # CS / AI / Physics — use OpenAlex (title search)
    ("deep_learning",         "openalex", "deep learning neural network"),
    ("transformer_llm",       "openalex", "transformer language model attention"),
    ("diffusion_models",      "openalex", "diffusion model generative image"),
    ("semiconductor_process", "openalex", "EUV lithography FinFET semiconductor fabrication"),
    ("gpu_computing",         "openalex", "GPU parallel computing CUDA graphics processor"),
    ("robotic_surgery",       "openalex", "robotic surgery surgical robot laparoscopic"),
    ("chip_eda",              "openalex", "electronic design automation chip synthesis"),

    # Biomedical — use PubMed (already working)
    ("glp1_agonists",          "pubmed", "GLP-1 receptor agonist OR semaglutide OR liraglutide OR exenatide"),
    ("checkpoint_inhibitors",  "pubmed", "PD-1 OR PD-L1 OR CTLA-4 AND checkpoint inhibitor AND cancer"),
    ("mrna_therapeutics",      "pubmed", "mRNA vaccine OR mRNA therapy OR lipid nanoparticle mRNA"),
    ("crispr",                 "pubmed", "CRISPR Cas9 OR CRISPR gene editing OR CRISPR therapy"),
    ("car_t_cell",             "pubmed", "CAR-T cell therapy OR chimeric antigen receptor T cell"),
    ("gene_therapy_aav",       "pubmed", "AAV gene therapy OR adeno-associated virus gene therapy"),
    ("cftr_modulators",        "pubmed", "CFTR modulator OR ivacaftor OR lumacaftor OR elexacaftor"),
    ("continuous_glucose",     "pubmed", "continuous glucose monitor OR CGM diabetes sensor"),
    ("protein_structure",      "pubmed", "protein structure prediction OR AlphaFold OR deep learning protein folding"),
    ("antibody_drug_conjugate","pubmed", "antibody-drug conjugate OR ADC cancer therapy"),
]


def openalex_count_year(query: str, year: int) -> int:
    """Count papers in OpenAlex matching keyword query in a given year."""
    params = {
        "filter": f"title_and_abstract.search:{query},publication_year:{year}",
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
            if source == "openalex":
                count = openalex_count_year(query, year)
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

    # Print summary: year of first acceleration (year where count doubles vs prior 3yr avg)
    print("\n=== ACCELERATION YEARS ===", file=sys.stderr)
    cluster_data = defaultdict(dict)
    for r in rows:
        cluster_data[r["cluster"]][int(r["year"])] = int(r["papers"])

    for cluster, year_counts in sorted(cluster_data.items()):
        sorted_years = sorted(year_counts)
        accel_year = None
        for i, y in enumerate(sorted_years):
            if i < 3:
                continue
            baseline = sum(year_counts[sorted_years[j]] for j in range(i-3, i)) / 3
            if baseline > 0 and year_counts[y] > baseline * 2:
                accel_year = y
                break
        peak_year = max(year_counts, key=lambda y: year_counts[y])
        peak_count = year_counts[peak_year]
        print(f"  {cluster:<30} accel={accel_year}  peak={peak_year} ({peak_count:,} papers)", file=sys.stderr)


if __name__ == "__main__":
    main()
