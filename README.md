# Trend Digest

A system that discovers trending topics across the web, curates them against a personal interest profile, and delivers them to Slack daily.

---

## Pipeline

```
# Tech digest
aggregate.py | curate.py --mode tech | deliver.py --mode tech

# News digest
aggregate.py | curate.py --mode news | deliver.py --mode news
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

## Social Platform Coverage

Evaluated platforms for trending signal accessibility (as of May 2026):

```
Platform    MAU      Trending  API         Science   Used
──────────────────────────────────────────────────────────────
Facebook    3.07B    Yes       Restricted  Low       No  — trending endpoint shut down 2018
WhatsApp    2.80B    No        No          None      No  — private messaging
YouTube     2.70B    Yes       Yes         Medium    Yes
Instagram   2.40B    Yes       Restricted  Low       No  — app review required, trending not exposed
TikTok      1.90B    Yes       Restrictive Low       No  — Research API requires approval
WeChat      1.40B    Yes       China-only  None      No
Telegram    0.95B    No        No          None      No
Messenger   0.94B    No        No          None      No  — private messaging
Snapchat    0.85B    Discover  No          None      No
Kuaishou    0.70B    Yes       China-only  None      No
Reddit      0.61B    Yes       Yes         High      Yes
Weibo       0.60B    Yes       China-only  None      No
X/Twitter   0.56B    Yes       Yes         High      Yes
Pinterest   0.54B    Yes       Yes         Low       No
Threads     0.40B    No        Limited     None      No  — API too early, trending not exposed
LinkedIn    0.31B    Yes       Restricted  Medium    No  — partner approval required
Discord     0.26B    No        No          None      No
Twitch      0.14B    Yes       Yes         Low       No
```

**Conclusion:** Reddit, X, and YouTube are the only platforms combining high MAU, accessible trending APIs, and meaningful signal. The rest are either locked down, China-only, or private messaging.

---

## Sources

Per-interest source lists (RSS feeds, subreddits, channels):

| Interest | Sources |
|---|---|
| Tech | [docs/sources/tech.md](docs/sources/tech.md) |
| AI / ML | [docs/sources/ai-ml.md](docs/sources/ai-ml.md) |
| Science | [docs/sources/science.md](docs/sources/science.md) |
| Finance | [docs/sources/finance.md](docs/sources/finance.md) |
| Geopolitics | [docs/sources/geopolitics.md](docs/sources/geopolitics.md) |
| Startups | [docs/sources/startups.md](docs/sources/startups.md) |
| Self-improvement | [docs/sources/self-improvement.md](docs/sources/self-improvement.md) |
| News | [docs/sources/news.md](docs/sources/news.md) |

---

## Setup

```bash
pip install feedparser
export SLACK_BOT_TOKEN=...
export YOUTUBE_API_KEY=...
```

Run the full pipeline:
```bash
python src/aggregate.py | python src/deliver.py
```

---

## Next Steps

- [ ] **Daily cron** — schedule the pipeline to run once per day
- [ ] **Reddit** — blocked from AWS IPs; needs proxy (`REDDIT_PROXY_URL` in `.env`) or API approval
- [ ] **Dev.to / Bluesky / Stack Overflow** — free APIs, ready to add fetchers
- [ ] **Other interest areas** — fetchers currently only cover tech; add science, finance, geopolitics sources
- [ ] **Delivery formats** — currently Slack only; newsletter, web page, or audio are future options
