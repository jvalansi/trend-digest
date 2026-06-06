#!/usr/bin/env python3
"""
Top global market cap gainers 2015-2025, covering non-US companies
accessible via yfinance (ADRs, direct US listings, OTC).

Output: data/global_value_creation.csv
"""

import csv
import math
import sys
import time
from datetime import date, timedelta

import yfinance as yf

OUTPUT = "/home/ubuntu/trend-digest/data/global_value_creation.csv"

# Non-US companies with US-accessible tickers
# Format: ticker, name, country, main_product, enabling_tech, underlying_science
COMPANIES = [
    # Semiconductors / hardware
    ("TSM",   "TSMC",              "Taiwan",      "contract chip manufacturing",         "EUV lithography + advanced node process",          "semiconductor physics + materials science"),
    ("ASML",  "ASML",              "Netherlands", "EUV lithography machines",             "extreme ultraviolet optics + plasma light source",  "plasma physics + optics + materials science"),
    ("005930.KS", "Samsung",       "South Korea", "memory + logic chips + smartphones",  "DRAM + NAND + foundry",                             "semiconductor physics + charge trapping"),

    # Pharma / biotech
    ("NVO",   "Novo Nordisk",      "Denmark",     "GLP-1 drugs (Ozempic/Wegovy)",        "peptide drug design + injection delivery",          "GLP-1 receptor biology + endocrinology"),
    ("BNTX",  "BioNTech",         "Germany",     "mRNA vaccines + cancer vaccines",      "lipid nanoparticle mRNA delivery",                  "mRNA biology + lipid chemistry"),
    ("AZN",   "AstraZeneca",      "UK",          "oncology + cardiovascular drugs",      "biologics + ADCs + gene therapy",                   "immunology + molecular biology"),
    ("RHHBY", "Roche",            "Switzerland", "cancer diagnostics + biologics",       "monoclonal antibodies + PCR diagnostics",           "immunology + molecular biology"),
    ("NVS",   "Novartis",         "Switzerland", "gene therapy + cardiovascular drugs",  "AAV gene therapy + small molecules",                "molecular biology + genetics"),
    ("GSK",   "GSK",              "UK",          "vaccines + specialty medicines",       "mRNA + adjuvant vaccine platforms",                 "immunology + molecular biology"),
    ("SNY",   "Sanofi",           "France",      "immunology + vaccines",               "monoclonal antibodies + mRNA vaccines",             "immunology + molecular biology"),
    ("BAYRY", "Bayer",            "Germany",     "pharma + crop science",               "small molecules + crop biotech",                    "medicinal chemistry + agrobiology"),

    # Tech platforms
    ("SHOP",  "Shopify",          "Canada",      "e-commerce platform",                 "SaaS + payments infrastructure",                    "none"),
    ("SAP",   "SAP",              "Germany",     "enterprise ERP + cloud",              "ERP software + cloud migration",                    "none"),
    ("MELI",  "MercadoLibre",     "Argentina",   "e-commerce + fintech (LatAm)",        "marketplace + payments platform",                   "none"),
    ("SE",    "Sea Limited",      "Singapore",   "gaming + e-commerce + fintech (SEA)", "mobile gaming + marketplace",                       "none"),
    ("INFY",  "Infosys",          "India",       "IT services + cloud consulting",      "software services",                                 "none"),

    # Chinese tech
    ("BABA",  "Alibaba",          "China",       "e-commerce + cloud (Alibaba Cloud)",  "cloud computing + recommendation algorithms",        "machine learning"),
    ("TCEHY", "Tencent",          "China",       "social media + gaming + fintech",     "social graph + mobile payments",                    "none"),
    ("PDD",   "PDD Holdings",     "China",       "e-commerce (Temu/Pinduoduo)",         "social commerce algorithms",                        "machine learning"),
    ("BIDU",  "Baidu",            "China",       "search + AI (ERNIE Bot)",             "search algorithms + LLMs",                          "information retrieval + deep learning"),

    # EV / clean energy
    ("NIO",   "NIO",              "China",       "electric vehicles",                   "battery swapping + EV platform",                    "electrochemistry"),
    ("XPEV",  "XPeng",            "China",       "electric vehicles + ADAS",            "EV + autonomous driving",                           "electrochemistry + deep learning"),

    # Industrial / energy
    ("SIEGY", "Siemens",          "Germany",     "industrial automation + energy",      "industrial IoT + power electronics",                "electrical engineering + control systems"),
    ("ABB",   "ABB",              "Switzerland", "robotics + electrification",          "industrial robots + grid tech",                     "electrical engineering + control systems"),

    # Consumer / luxury
    ("LVMUY", "LVMH",             "France",      "luxury goods",                        "none",                                              "none"),
    ("TM",    "Toyota",           "Japan",       "ICE + hybrid + hydrogen vehicles",    "hybrid drivetrain + fuel cell",                     "electrochemistry + mechanical engineering"),
    ("SONY",  "Sony",             "Japan",       "gaming + imaging + entertainment",    "CMOS image sensors + PlayStation platform",          "semiconductor physics + optics"),
]

START_DATE = "2015-01-02"
END_DATE   = "2025-01-02"


def get_price(ticker: str, target_date: str, retries: int = 3) -> float | None:
    end_dt = date.fromisoformat(target_date) + timedelta(days=12)
    for attempt in range(retries):
        try:
            df = yf.download([ticker], start=target_date, end=end_dt.isoformat(),
                             auto_adjust=True, progress=False, threads=False)
            if df.empty:
                return None
            val = df["Close"].iloc[0]
            if hasattr(val, "__len__"):
                val = val.iloc[0]
            return float(val) if not math.isnan(float(val)) else None
        except Exception as e:
            if "Rate" in str(e) and attempt < retries - 1:
                time.sleep(8 * (attempt + 1))
                continue
            return None
    return None


def get_fast_info(ticker: str, retries: int = 3) -> tuple:
    for attempt in range(retries):
        try:
            fi = yf.Ticker(ticker).fast_info
            mc = getattr(fi, "market_cap", None)
            lp = getattr(fi, "last_price", None)
            if mc and lp and mc > 0 and lp > 0:
                return float(mc), float(lp)
            return None, None
        except Exception as e:
            if "Rate" in str(e) and attempt < retries - 1:
                time.sleep(8 * (attempt + 1))
                continue
            return None, None
    return None, None


def main():
    results = []
    total = len(COMPANIES)

    for i, (ticker, name, country, product, tech, science) in enumerate(COMPANIES):
        print(f"[{i+1}/{total}] {ticker} ({name})...", file=sys.stderr)

        mc, lp = get_fast_info(ticker)
        time.sleep(1.5)
        p_start = get_price(ticker, START_DATE)
        time.sleep(1.5)
        p_end = get_price(ticker, END_DATE)
        time.sleep(1.5)

        if not (mc and lp and p_start and p_end and lp > 0):
            print(f"  SKIP — missing data (mc={mc}, lp={lp}, p_start={p_start}, p_end={p_end})", file=sys.stderr)
            continue

        start_mcap = mc * (p_start / lp) / 1e9
        end_mcap   = mc * (p_end   / lp) / 1e9
        value_created = end_mcap - start_mcap

        print(f"  start=${start_mcap:.0f}B  end=${end_mcap:.0f}B  gain=+${value_created:.0f}B", file=sys.stderr)

        results.append({
            "ticker": ticker,
            "name": name,
            "country": country,
            "main_product": product,
            "enabling_tech": tech,
            "underlying_science": science,
            "start_mcap_b": round(start_mcap, 1),
            "end_mcap_b": round(end_mcap, 1),
            "value_created_b": round(value_created, 1),
        })

    results.sort(key=lambda x: x["value_created_b"], reverse=True)

    print(f"\n=== TOP GLOBAL NON-US GAINERS 2015-2025 ===", file=sys.stderr)
    for i, r in enumerate(results):
        print(f"  #{i+1:2d} {r['ticker']:8} {r['name'][:22]:22} +${r['value_created_b']:>6,.0f}B  {r['underlying_science'][:40]}", file=sys.stderr)

    fieldnames = ["ticker", "name", "country", "main_product", "enabling_tech",
                  "underlying_science", "start_mcap_b", "end_mcap_b", "value_created_b"]
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nWrote {len(results)} rows to {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
