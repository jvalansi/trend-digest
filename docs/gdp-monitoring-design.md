# GDP Monitoring System — Design Discussion

A conversation exploring how to build a real-time global economic monitoring system grounded in historical GDP data.

---

## The Core Idea

Track what's happening in the world by monitoring economic signals — starting from historical GDP data as context, then layering real-time indicators to detect meaningful changes as they happen.

---

## Historical Layer — Maddison Project Data

The [Maddison Project Database](https://www.rug.nl/ggdc/historicaldevelopment/maddison/) provides GDP per capita estimates going back to 1 AD for most countries. Key findings from the data:

- **Pre-1800: Malthusian trap** — GDP per capita was essentially flat everywhere for centuries. Population growth absorbed productivity gains, keeping living standards stagnant.
- **Pre-industrial GDP ≈ population × subsistence output** — China and India were the largest economies in absolute terms simply because they had the most people.
- **The Great Divergence (~1800)** — the Industrial Revolution broke the Malthusian trap. Western Europe and its offshoots grew productivity faster than population, creating a compounding advantage that widened dramatically through the 19th century.
- **Recent convergence** — China, Japan, South Korea, and Taiwan have followed the same institutional playbook and are closing the gap. China's GDP per capita trajectory since Deng's 1978 reforms is the most dramatic economic event of the last 50 years.

### Why the West Diverged

The chain of causation, working backwards:

1. **Industrial Revolution** (~1760–1850) — compounding productivity growth from machines
2. **Merchant oligarchy with political power** — property rights protected, capital could accumulate safely
3. **Atlantic trade and colonial system** — cheap inputs (slave labor, raw materials), captive markets, demand that justified scaling production
4. **Discovery of the Americas** (~1492) — itself driven by the desire to find sea routes to Asia and cut out Ottoman/Islamic middlemen on overland trade
5. **Italian city-states** (~1000–1300) — the first places in Europe where merchants *were* the government; enabled by Rome's political collapse creating a power vacuum, while preserving Roman institutional and legal memory
6. **Rome's fall** — paradoxically necessary: Roman unity would have prevented independent city-states from forming, but Roman cultural continuity provided the institutional foundation

**Key insight:** Western dominance may be less the result of cultural superiority and more the result of a lucky geographic chain reaction — Columbus miscalculated the Earth's size and accidentally found a continent in the way. The Industrial Revolution then compounded this advantage over 300 years.

**Current moment:** China's rapid catch-up looks less like an anomaly and more like a reversion to the historical mean.

### Zheng He Counterfactual

China sent massive fleets to Southeast Asia, India, Arabia, and East Africa (1405–1433) — before Columbus, with far larger ships. Then stopped by imperial decree. The voyages were state prestige projects, not commercially driven. No merchants were getting rich and lobbying to continue. Confucian ideology ranked merchants at the bottom of the social hierarchy.

This is the clearest counterfactual in history: China had the ships and the navigational capability. What it lacked was a merchant class with political power to sustain the project. The same institutional difference — merchants with vs without political power — explains both why Europe found America and why China didn't.

---

## Real-Time Signal Layer

### The Goal

Detect meaningful economic changes as they happen — weeks or months before official GDP figures are published — and explain them in historical context.

### Signal Stack

Two primary signals cover most of the world with free data:

**Electricity consumption** (physical economy)
- Correlates ~0.95 with GDP in industrial economies
- IEA publishes monthly data for ~80 countries, free
- Harder to fake than official GDP — governments misreport statistics, power grids don't lie
- Li Keqiang famously used this instead of official Chinese GDP figures
- Limitation: developed economies are decoupling electricity from GDP as services dominate

**Mobility data** (consumer economy)
- Google Mobility Reports: ~180 countries, daily, free
- Measures retail, workplace, transit, residential activity separately
- Captures the consumption (C) component that electricity misses
- Orthogonal to electricity: a busy shopping district has high mobility, modest electricity

These two signals are more independent than electricity + web traffic (which both rise with general economic activity and overlap heavily).

### Fallback for Missing Coverage

| Tier | Countries | Signals |
|---|---|---|
| Tier 1 | ~80 major economies | Electricity + mobility |
| Tier 2 | ~100 smaller economies | Mobility + nighttime lights |
| Tier 3 | ~handful (North Korea etc.) | Nighttime lights only |

**NASA Black Marble** (nighttime lights) covers every country on Earth, monthly, free. Researchers have used it to detect economic activity in North Korea, measure hurricane recovery, and cross-check countries suspected of misreporting GDP.

### Attribution Layer

Detecting *that* something changed is easy. Knowing *why* requires a news layer.

Two complementary sources cover different event types:

**Wikipedia page views** (primary attribution — live and backtesting)
- Wikimedia API returns the top 1000 most-viewed articles for any language edition on any given day, ~1 day lag for live use, back to 2015 for backtesting — no keywords needed, fully open-ended
- Language editions map to countries: `vi.wikipedia` → Vietnam, `ar.wikipedia` → Arabic-speaking world, etc.
- Captures the full event spectrum: conflicts, tech launches, economic events, natural disasters, political crises
- Reflects deliberate information-seeking (stronger signal than search volume)
- Official API — more stable and reliable than pytrends (which scrapes Google unofficially)
- Free, no auth required
- Proof of concept: ChatGPT article went from 2,074 views on Dec 5 2022 (launch day) to #8 globally on Jan 17 2023 (226k views), and #2 on Feb 9 2023 (310k views) — a clear signal GDELT entirely missed

```
Signal anomaly detected (e.g. Vietnam electricity -15%)
→ Pull top Wikipedia articles for vi.wikipedia that week
→ Claude: "Top article: 'Bão Yagi' (Typhoon Yagi) — made landfall, disrupting industrial zones in the north"
```

```python
# Top articles for a language edition on a given day (no keywords needed)
GET https://wikimedia.org/api/rest_v1/metrics/pageviews/top/vi.wikipedia/all-access/2024/09/07

# Specific article history for validation/backtesting
GET https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/ChatGPT/daily/20221201/20230331
```

**Google Trends trending searches** (supplementary live attribution)
- `pytrends.trending_searches(pn='vietnam')` returns what's trending in a country on a given day
- Useful as a cross-check, especially for countries with low Wikipedia language edition coverage
- Limitation: unofficial scraper, rate-limited, shallow historical archive (~24 hours), periodically breaks

**GDELT** (backtesting and conflict attribution)
- Monitors 100+ languages, 65,000+ news sources globally, codes every event by country/type/intensity, updates every 15 minutes, completely free
- Deep historical archive (1979–present, 876M+ events) — essential for validating the system against known past shocks
- Strongest signal for kinetic conflict events (wars, bombings, coups); weaker for economic/tech disruptions
- Known limitation: English-language bias inflates US domestic events; tech events (e.g. ChatGPT launch) are nearly invisible to its NLP pipeline

```
Backtesting: Vietnam electricity -15% in Sept 2024
→ Pull GDELT events for Vietnam, Sept 2024
→ Confirm: Typhoon Yagi (GoldsteinScale -9.4, 180k mentions) matches anomaly date
```

**GDELT event intensity findings** (from empirical analysis of `gdelt-bq.full.events`, 876M rows):
- Most intense events by normalized mention share (% of global news): Gulf War Feb 1991 (3.4%), Oct 2023 Gaza war (3.4%), 2006 Lebanon War (3.1%)
- Most negative Goldstein scale pre-internet: Halabja chemical attack, Iraq March 1988 (-9.84)
- Pre-2000 data is sparse due to limited newspaper digitization; 1930s–1960s have virtually no coverage
- Media volume scaled ~1000× from 1980s to 2020s — always normalize by total monthly volume when comparing across eras

---

## System Architecture

```
Data layer:
  - IEA electricity consumption          (80 countries, monthly)
  - Google Mobility Reports              (180 countries, daily)
  - NASA Black Marble lights             (global, monthly, fallback)
  - Wikipedia top articles               (global, daily, live + backtesting attribution — primary)
  - Google Trends trending searches      (supplementary live attribution)
  - GDELT news events                    (global, real-time, conflict attribution + backtesting)
  - Maddison historical data             (context layer, static)

Processing layer:
  - Detect anomalies vs 90-day rolling average per country
  - Rank by deviation magnitude
  - Pull Wikipedia top articles for anomalous countries (live + backtesting, all event types)
  - Pull GDELT events for anomalous countries (conflict validation)
  - Pull Google Trends trending searches as cross-check where Wikipedia coverage is thin
  - Claude synthesizes signal + news into attribution + historical context

Output layer:
  - Daily Slack digest: top 5-10 movers with 2-3 sentence explanation
  - On-demand: drill into any country's signal history + Maddison arc
```

### Example Digest Entry

> 🔴 **Pakistan** — electricity -18%, mobility -12%
> Flooding in Punjab disrupted grid infrastructure and kept people home. Pakistan has experienced 3 major flood events in the last decade; each has shaved 1-2% off annual GDP.

> 🟢 **Vietnam** — electricity +9%, mobility +6%
> Samsung factory expansion coming online in Hanoi province. Vietnam is following the same export-led manufacturing trajectory as South Korea in the 1970s — currently growing at ~7% annually.

---

## Plan

### Phase 1 — Attribution layer (highest leverage, start here)
The attribution layer is the core value-add. Build and validate it before investing in signal fetchers.

- [ ] **Wikipedia fetcher** — `GET /metrics/pageviews/top/{lang}.wikipedia/all-access/{date}` for top articles per language edition; build country → language edition mapping (e.g. Vietnam → `vi`, Iraq → `ar`, Russia → `ru`)
- [ ] **Backtest attribution** — for 5–10 known historical shocks (Typhoon Yagi Sept 2024, Ukraine invasion Feb 2022, ChatGPT Dec 2022, etc.), verify Wikipedia top articles correctly surface the cause within ±3 days of the signal anomaly
- [ ] **GDELT fetcher** — query `gdelt-bq.full.events` for conflict-specific attribution; GCP project `optimum-lodge-278819` already authenticated with BigQuery access
- [ ] **Google Trends fetcher** — `pytrends.trending_searches()` as supplementary signal for countries with thin Wikipedia coverage

### Phase 2 — Signal layer
- [ ] **Electricity fetcher** — IEA Monthly Electricity Statistics API (~80 countries, monthly, ~6 week lag)
- [ ] **Mobility fetcher** — Google Mobility Reports CSV (~180 countries, daily, ~2 day lag)
- [ ] **Nighttime lights fetcher** — NASA Black Marble (~global, monthly, fallback for Tier 3 countries)
- [ ] **Anomaly detection** — rolling z-score per country per signal; flag >2σ moves; combine signals into a composite score

### Phase 3 — Integration
- [ ] **Historical context** — given a country + anomaly, pull its Maddison arc and key inflection points for Claude to use as background
- [ ] **Pipeline integration** — wire into existing trend-digest as a new digest mode; daily Slack output: top 5–10 country movers with attribution + historical context

---

## GDP Component Framework

GDP decomposes into four components (expenditure approach):

| Component | Driven by | Available signal |
|---|---|---|
| **C** — Consumer spending | Wages from company revenue | Google Mobility (retail/workplace) |
| **I** — Private investment | Retained earnings + debt | Electricity consumption (industrial load) |
| **G** — Government spending | Tax revenue (redistributive) | Set aside — funded by C+I tax base |
| **NX** — Net exports | Trade flows | WTO trade stats, AIS ship tracking — **currently unmonitored** |

**Why not use company earnings directly?**
Public companies account for only ~20–25% of US GDP (value-added basis, per NBER), and the fraction is lower in most other economies. Earnings data gives a biased sample — large, listed, export-oriented firms — and systematically misses SMEs, private companies, and the informal economy. Physical signals (electricity, mobility) capture the full 100% of activity regardless of listing status.

Earnings data is most useful as an **attribution layer**: once a physical signal anomaly is detected, sector-level earnings can confirm which industries drove it.

**Real vs. nominal GDP**
Productivity gains in existing sectors tend to be competed away into lower prices (more output × lower price = flat revenue). Nominal GDP growth requires credit expansion — banks creating new money faster than output grows. This is why central banks target ~2% inflation: deliberately expanding money supply ~5% against ~3% real output growth. Real GDP (inflation-adjusted) strips this out and is the better measure of actual output growth. Real hourly wages — how much real stuff an hour of labor buys — is arguably the most honest single measure of whether growth reaches people.

---

*For broader theoretical context — welfare beyond GDP, civilization trajectory, historical frameworks, r > g inequality dynamics, and how to think about predicting history — see `llm-wiki/wiki/topics/history-theory.md`.*

