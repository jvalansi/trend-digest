# Video Digest — Plan

A system that generates personalized short videos on topics that would interest the user, replacing passive YouTube scrolling with curated, auto-generated content.

---

## Pipeline Overview

```
Topic Discovery → Curation & Scoring → Script Generation → Video Synthesis → Delivery
```

---

## Phase 1: Topic Discovery

Identify what's happening and trending across multiple sources.

### News & Current Events
- **Wikipedia Trending** — what people are actually looking up (high signal, slightly lagged)
- **X (Twitter) Trending** — real-time public discourse
- **Google Trends** — search interest spikes

### Tech
- **Hacker News** — top/new stories (Algolia API, no auth needed)
- **GitHub Trending** — repos gaining stars (new tools, frameworks)
- **Reddit** — r/technology, r/programming, r/MachineLearning etc.
- **Product Hunt** — new product launches
- **Lobste.rs** — higher signal tech link aggregator

### Science
- **ArXiv** (cs.AI, cs.LG, q-bio, physics) — preprints before media coverage
- **Papers With Code** — ML papers with implementations
- **Nature / Science RSS** — peer-reviewed breakthroughs
- **Phys.org** — broad science news

### Trending Websites (cross-category signal)
- **Cloudflare Radar** (`trending_rise`) — domains with sudden traffic spikes, filtered by category
  - API: `GET /radar/ranking/top?rankingType=trending_rise`
  - Categories: Technology, News & Media, Science, etc.
- **SimilarWeb** — category-level popularity rankings (monthly baseline)

---

## Phase 2: Curation & Scoring

Use Claude to:
1. Deduplicate overlapping stories across sources
2. Score each topic against a user interest profile
3. Select top N topics per day (e.g. 5–10)

**Interest profile** (to be refined over time):
- AI / ML research and tools
- Geopolitics and global news
- Science (longevity, physics, biology)
- Startups and tech products
- Self-improvement / productivity
- Finance and markets

---

## Phase 3: Script Generation

For each selected topic:
1. Pull full context from Wikipedia + source articles
2. Claude writes a 2–5 min narration script
3. Include hook, body, key facts, and a takeaway

---

## Phase 4: Video Synthesis

- **Narration:** ElevenLabs TTS (or Kokoro for local/free)
- **Visuals:** Stock footage from Pexels API (free, keyword-matched)
- **Assembly:** `moviepy` + `ffmpeg`
- **Output format:** MP4, ~2–5 min per topic

---

## Phase 5: Delivery

- Drop videos to a shared folder / S3
- Post links to Slack (`#proj-video-digest`)
- Run daily as a scheduled job (cron or systemd timer)

---

## Implementation Order

1. **Topic discovery script** — pull from 3–4 sources, output ranked list
2. **Curation layer** — Claude scoring against interest profile
3. **Script generator** — Claude writes narration
4. **TTS** — ElevenLabs API
5. **Video assembly** — moviepy + Pexels b-roll
6. **Scheduler** — daily cron job
7. **Slack delivery** — post to channel

---

## Notes

- Cloudflare Radar API token available (free tier, `Read Cloudflare Radar data` permission)
- Reddit tool available at `/home/ubuntu/reddit-tool/`
- Validation tool (HN, Google Trends, Product Hunt, Reddit) at `/home/ubuntu/validation-tool/`
- Keep topic discovery modular — each source is a separate function
