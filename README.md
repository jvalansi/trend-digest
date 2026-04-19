# Trend Digest

A system that discovers trending topics across the web, curates them against a personal interest profile, and delivers them to Slack daily.

---

## Pipeline

```
aggregate.py | curate.py | deliver.py
```

### Phase 1 — Fetch & Aggregate (`aggregate.py`)

Runs all fetchers in parallel, merges output, groups near-duplicate stories, and scores each item:

```
score = (engagement_z + cross_source_bonus) * authority * recency
```

- **Engagement** — normalized z-score via Welford running stats (per source), stored in `data/engagement_stats.json`
- **Cross-source bonus** — `log(1 + mentions - 1)`: if multiple sources cover the same story, score rises
- **Authority** — per-source weight (MIT Tech Review = 1.2, HN = 1.3, ZDNet = 0.7, etc.)
- **Recency** — exponential decay, score halves every 12h

### Phase 2 — Curate (`curate.py`)

Sends top N items to Claude with the interest profile. Claude scores each item 0–1 for relevance. Final score:

```
final_score = engagement_score * (0.3 + 0.7 * relevance)
```

Interest profile: AI/ML, geopolitics, science, startups, finance, self-improvement.

### Phase 3 — Deliver (`deliver.py`)

Claude generates a one-sentence description per item. Posts to `#proj-trend-digest` as a formatted Slack message.

---

## Fetchers

| Fetcher | Source | Engagement Signal | Notes |
|---|---|---|---|
| `fetchers/rss.py` | 8 tech RSS feeds | Cross-source mentions + recency | feedparser |
| `fetchers/hn.py` | Hacker News top/new/best | HN score | Firebase REST API, no auth |
| `fetchers/youtube.py` | 6 curated channels | View count | playlistItems (1 unit/channel), 24h cache |
| `fetchers/github.py` | GitHub Trending | Stars today | HTML scrape |

All fetchers output the same normalized format:
```json
{ "title", "summary", "url", "source", "category", "engagement", "fetched_at", "published_at" }
```

### `fetchers/stats.py`

Shared Welford running-stats module. Maintains per-source mean/variance in `data/engagement_stats.json`, updated on every fetch. Used by all fetchers to produce a comparable engagement z-score.

---

## Sources

Per-interest source lists (RSS feeds, subreddits, channels):

| Interest | Sources |
|---|---|
| Tech | [sources/tech.md](sources/tech.md) |
| AI / ML | [sources/ai-ml.md](sources/ai-ml.md) |
| Science | [sources/science.md](sources/science.md) |
| Finance | [sources/finance.md](sources/finance.md) |
| Geopolitics | [sources/geopolitics.md](sources/geopolitics.md) |
| Startups | [sources/startups.md](sources/startups.md) |
| Self-improvement | [sources/self-improvement.md](sources/self-improvement.md) |

---

## Setup

```bash
pip install feedparser
export SLACK_BOT_TOKEN=...
export YOUTUBE_API_KEY=...
```

Run the full pipeline:
```bash
python aggregate.py | python curate.py | python deliver.py
```

---

## Next Steps

- [ ] **Daily cron** — schedule the pipeline to run once per day
- [ ] **Reddit** — blocked from AWS IPs; needs proxy (`REDDIT_PROXY_URL` in `.env`) or API approval
- [ ] **Dev.to / Bluesky / Stack Overflow** — free APIs, ready to add fetchers
- [ ] **Other interest areas** — fetchers currently only cover tech; add science, finance, geopolitics sources
- [ ] **Delivery formats** — currently Slack only; newsletter, web page, or audio are future options
