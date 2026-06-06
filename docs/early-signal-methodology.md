# Early Signal Detection — Methodology

How to identify scientific fields that are about to matter commercially, before they become mainstream.

---

## Core Premise

From the S&P 500 analysis: the underlying science for most commercial breakthroughs was established 5–40 years before mainstream adoption. The question is whether there's a detectable signal in the academic literature that precedes the commercial explosion — and if so, how early.

**Confirmed examples:**
- Deep learning: AlexNet 2012 → ChatGPT 2022 (~10 year lag)
- Semaglutide: SUSTAIN phase 3 trials ~2015–2016 → Ozempic mainstream 2023 (~7 year lag)
- CRISPR: structural acceleration ~2013 → first approved therapy 2023 (~10 year lag)

---

## Data Source: OpenAlex

OpenAlex is a free, fully open academic paper index (~250M works). It tags every paper with **concept IDs** derived from citation communities — not keyword matching. This makes concept IDs more precise than keyword search: the field boundary is defined by who cites whom, not by vocabulary.

- API: `https://api.openalex.org`
- Rate limit: 10 req/sec (no auth required; add `mailto=` param to be polite)
- 65,026 concepts total; levels 0 (broadest) through 5 (most specific)
- Level 3 has 24,749 concepts — the most useful resolution for field-level signals

---

## Key Finding: Granularity Matters

**Broad concept IDs mask inflections.** The `glp1_agonists` concept (`C2776398474`, "Glucagon-like peptide-1") shows steady, unbroken growth from 142 papers/year in 2000 to 703 in 2023. No explosion visible. This is because GLP-1 biology has been studied since the 1980s — the concept captures the entire field history.

**Specific concept IDs show clean signals.** The `semaglutide` concept (`C2909862629`) shows:

| Year | Papers |
|------|--------|
| 2010 | 3 |
| 2012 | 2 |
| 2014 | 5 |
| 2016 | 54 |
| 2018 | 165 |
| 2020 | 316 |
| 2022 | 599 |
| 2024 | 1,419 |

The inflection at 2015–2016 corresponds to the SUSTAIN phase 3 trial period — 7 years before the Ozempic mainstream moment.

**Rule: for drug fields, track the specific molecule, not the underlying biology.**

The same principle applies to technology fields: "deep learning" (C108583219) is more useful than "artificial intelligence" (C154945302) for detecting early acceleration.

---

## Validating the Signal: Control Experiment

Mature, unexciting fields should show flat or slow linear growth. Results for 2020→2024:

| Concept | 2020 | 2024 | Ratio |
|---------|------|------|-------|
| Fluid dynamics | 367k | 572k | 1.6× |
| Thermodynamics | 228k | 217k | 0.95× |
| Hypertension | 108k | 88k | 0.8× |
| Statistics | 395k | 273k | 0.7× |

Global publication volume grows ~3–4%/year, so a 5-year baseline ratio is ~1.15–1.22×. Anything above **3–4× over 5 years** is a meaningful signal above noise.

Semaglutide's ratio over the same window: **316 → 1,419 = 4.5×** (and ~466× from its near-zero 2010 baseline).

---

## Acceleration Detection: Piecewise Log-Linear Breakpoint

For clusters with full year-by-year data (2000–2024), acceleration is detected by fitting two log-linear segments and finding the split that minimizes total SSE.

A breakpoint is reported if either condition holds:

**(a) Slope acceleration** — post-breakpoint slope ≥ 1.1× pre-breakpoint slope

**(b) Level shift** — right segment's predicted value at the breakpoint is ≥ 0.7 log-units (~2×) above left segment's prediction at that point. Catches fields that show a sudden step-up in absolute count even without a slope change.

Results on current clusters:

| Cluster | Accel Year | Signal |
|---------|-----------|--------|
| car_t_cell | 2012 | level-shift |
| crispr | 2013 | slope×1.29 + level |
| immune_checkpoint | 2014 | level-shift |
| deep_learning | 2015 | slope×2.0 |
| cftr_modulators | 2017 | slope×2.97 |
| language_model_llm | 2018 | slope×3.77 |

---

## Planned: Full Science Sweep

To surface *unknown* exploding fields rather than validating known ones, the plan is to sweep all 24,749 level-3 OpenAlex concepts monthly.

**Mechanics:**
- ~1,000 concepts/day → full sweep in ~25 days, repeated monthly
- Per concept: fetch paper counts for 3 snapshots (2019, 2022, 2024)
- 2,000–3,000 API calls/day at 0.1s/call = ~3–5 minutes/day
- Output: ranked list of concepts by 2019→2024 growth ratio

**Threshold for "exploding":**
- ≥ 200 papers in 2024 (minimum signal floor)
- 2024 / 2019 ratio ≥ 3–4× (above publication-volume baseline)
- Interesting zone: **5–50×** — large enough to be real, small enough that mainstream hasn't noticed

**Known artifact to filter:** OpenAlex occasionally reassigns concept tags in bulk, causing apparent step-changes that aren't real. Extreme ratios (>100×) should be cross-checked against prior-year data before being treated as signals.
