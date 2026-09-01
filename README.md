# Trend Digest

A system that discovers trending topics across the web — news, science papers, markets, GitHub repos, prediction markets, social platforms — curates them against a personal interest profile, and delivers a daily digest to Slack / Discord / Telegram / Medium.

---

## Pipeline

```
run_digest.sh <mode>
   ├─ src/aggregate.py  →  fetches from N sources, scores, ranks
   ├─ src/curate.py     →  Claude scores each item 0–1 for relevance, re-ranks
   └─ src/deliver.py    →  Claude writes one-sentence descriptions, posts to channel
```

Cron (UTC, weekdays + Sunday):

```
13:00  tech
13:15  news
13:30  finance
13:45  science
```

---

## Modes

Each mode picks a different fetcher mix and interest profile.

| Mode | Profile | Default channel |
|---|---|---|
| `tech` | AI/ML, dev tools, startups, security, hardware, science | `#proj-trend-digest` |
| `news` | World events, geopolitics, elections, markets, climate, culture | `#proj-news-digest` |
| `science` | Bio, physics, climate, neuroscience, medicine, preprints | `#proj-trend-digest` |
| `finance` | Markets, macro, unusual flow, central banks, prediction odds | `#proj-trend-digest` |

---

## Fetchers

21 fetchers, all output the same normalized format:

```json
{ "title", "summary", "url", "source", "category",
  "engagement", "engagement_raw", "fetched_at", "published_at" }
```

| Family | Fetcher | Source |
|---|---|---|
| RSS | `rss.py` | Per-category feed lists in `docs/sources/*.md` |
| News aggregators | `hn.py` | Hacker News (top/new/best) |
| Trends | `trends_google.py` / `trends_google_global.py` | Google Trends (US + global) |
| Trends | `trends_wikipedia.py` | Wikipedia top-viewed articles |
| Trends | `trends_reddit.py` | Per-mode subreddit lists |
| Trends | `trends_bilibili.py` | Bilibili trending (Chinese) |
| Video | `youtube.py` | Curated channels, by category |
| Social | `x.py` | X/Twitter via Grok |
| Code | `github.py` | GitHub Trending (daily + weekly) |
| Papers | `arxiv.py` | arXiv recent |
| Papers | `arxiv_ngram_burst.py` | n-gram burst detection across arXiv taxonomy |
| Papers | `biorxiv.py` | bioRxiv recent |
| Papers | `openalex.py` / `openalex_early_signal.py` | OpenAlex concept-share early-signal sweep |
| Papers | `semantic_scholar.py` | Highly-cited recent papers |
| Papers | `altmetric.py` | High-attention papers |
| AI | `hf_papers.py` / `hf_models.py` | HuggingFace daily papers + trending models |
| Finance | `etf_volume.py` | Unusual ETF volume relative to 30d baseline |
| Markets | `polymarket.py` | Recent prediction-market probability moves |

### Two output classes

`aggregate.py` produces a sectioned format:

```json
{
  "rss": [ ... merged, deduped RSS pool ... ],
  "sections": {
    "Hacker News":            [ ... ],
    "GitHub Trending":        [ ... ],
    "arXiv n-gram Burst":     [ ... ],
    "OpenAlex Early Signal":  [ ... ],
    ...
  }
}
```

- **RSS pool** — feeds from multiple sources are *merged* (near-duplicate stories cluster together by title-word Jaccard ≥ 0.25), then scored by cross-source agreement.
- **Sections** — each fetcher is its own discovery channel. Items are deduped by URL within a section but kept distinct; the section identity is itself the signal.

### Burst-detection fetchers

`arxiv_ngram_burst.py` and `openalex_early_signal.py` are discovery channels, not feeds. They sweep the full arXiv (146 categories) / OpenAlex (24,749 L3 concepts) taxonomy by deterministic daily partition — on weekday N of the quarter, the slice `concepts[N·T/D : (N+1)·T/D]` runs (sorted by ID for reproducibility). Each scan compares paper share in a recent window to a historical baseline (1y prior for arxiv, 5y prior for openalex) and flags concepts whose share has grown 5–50× while normalizing against overall corpus growth. No mutable state — same date + same code → same partition. See `docs/early-signal-methodology.md`.

---

## Scoring

### Phase 1 — Aggregate (`aggregate.py`)

**RSS pool:**

```
score = (1 + cross_source_bonus) × authority × recency
cross_source_bonus = log(1 + n_sources - 1)
authority          = per-source weight (see SOURCE_AUTHORITY in aggregate.py)
recency            = exp(-Δhours · ln(2)/12)   # halves every 12h
```

RSS items have no native engagement signal, so cross-source agreement is the signal.

**Sections:**

Each fetcher z-scores its own items via `fetchers/stats.py` (Welford online stats persisted in `data/engagement_stats.json`), clamped to [-3, 3]. `engagement` is the z-score; `engagement_raw` is the original count. Sections are deduped by URL and top-N within each section.

### Phase 2 — Curate (`curate.py`)

Claude scores every item 0.0–1.0 for relevance to the mode's profile. Final score:

```
score = base × (0.3 + 0.7 × relevance)
```

where `base` is the aggregate score for RSS items, or `max(0, engagement)` for section items. Both RSS and sections are now re-ranked by this final score. For `news` mode, Claude also translates non-English titles to English.

### Phase 3 — Deliver (`deliver.py`)

Claude generates a one-sentence description per item. Items are annotated with `days_since_first_seen` (from `data/seen_items.json`) so repeats are visible. Posts to the configured Slack / Discord / Telegram / Medium channel.

---

## Delivery targets

`deliver.py` flags:

| Flag | Target |
|---|---|
| (default) | Slack |
| `--discord` | Discord (header + threaded items) |
| `--telegram` | Telegram via cc-connect |
| `--publish` | Medium post + cross-posts to Bluesky / LinkedIn / Reddit |
| `--dry-run` | Print to stdout, no network |

Publishers live in `src/publishers/`: `medium.py`, `bluesky.py`, `linkedin.py`, `reddit.py`.

---

## Setup

```bash
pip install feedparser deep-translator langdetect
```

Environment (in `~/.env` or repo-level `.env`):

```
# Core
SLACK_BOT_TOKEN=...
YOUTUBE_API_KEY=...
XAI_API_KEY=...                 # x.py uses Grok
FMP_API_KEY=...                 # etf_volume.py
PEXELS_API_KEY=...              # OG-image fallback
REDDIT_PROXY_URL=...            # Reddit blocks AWS IPs; needs proxy

# Delivery targets (optional, per-flag)
DISCORD_BOT_TOKEN=...           # --discord
MEDIUM_TOKEN=...                # --publish
BSKY_HANDLE=... BSKY_APP_PASSWORD=...
LINKEDIN_ACCESS_TOKEN=... LINKEDIN_PERSON_URN=...
REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=...
REDDIT_USERNAME=... REDDIT_PASSWORD=...
```

The `claude` CLI is invoked as a subprocess by `curate.py` and `deliver.py`; path is `CLAUDE_PATH` (defaults to `/home/ubuntu/.local/bin/claude`).

Run a full pipeline:

```bash
./run_digest.sh tech                  # hardcodes --discord --publish
python src/deliver.py --input curated.json --mode tech --dry-run  # preview only
```

---

## Layout

```
src/
  aggregate.py            fetcher orchestration + RSS merge + scoring
  curate.py               Claude relevance scoring
  deliver.py              description generation + channel posting
  fetchers/               22 fetcher modules + stats.py (Welford)
  publishers/             medium / bluesky / linkedin / reddit
data/
  engagement_stats.json   Welford state per source (per-fetcher z-score)
  seen_items.json         URL → first_seen / last_seen / count
  openalex_concepts_l3.json  cached L3 concept list (refreshed every 30d)
  arxiv_categories.json   cached arXiv taxonomy
  global_trends/          daily Google Trends Global archive (for clustering)
docs/
  sources/                per-mode source lists
  early-signal-methodology.md   burst-detection design
  gdp-monitoring-design.md / early-signal-methodology.md ...  design docs (general essays live in llm-wiki/wiki/topics/)
research/                 standalone analysis scripts
```

---

## Social platform coverage

Reddit, X, and YouTube are the only platforms that combine high MAU, an accessible trending API, and meaningful signal. The rest are locked down, China-only, or private messaging.

```
Platform    MAU     Trending  API          Used
─────────────────────────────────────────────────────
YouTube     2.70B   yes       yes          ✓
Reddit      0.61B   yes       yes          ✓ (via proxy — AWS IPs blocked)
X/Twitter   0.56B   yes       yes (Grok)   ✓
Facebook    3.07B   yes       restricted   ✗  trending endpoint shut 2018
Instagram   2.40B   yes       restricted   ✗  app review required
TikTok      1.90B   yes       restricted   ✗  Research API requires approval
WeChat/Weibo/Bilibili/Kuaishou      yes   China-only  Bilibili used; rest no
LinkedIn    0.31B   yes       restricted   ✗  partner approval required
Threads     0.40B   no        limited      ✗  trending not exposed
WhatsApp / Telegram / Messenger / Discord / Snapchat — private, no trending
```
