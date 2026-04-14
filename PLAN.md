# Video Digest — Plan

A system that generates personalized short videos on topics that would interest the user, replacing passive YouTube scrolling with curated, auto-generated content.

---

## Pipeline Overview

```
Topic Discovery → Curation & Scoring → Script Generation → Video Synthesis → Delivery
```

---

## Phase 1: Topic Discovery

Rather than hardcoding sources heuristically, we use traffic data to discover the most popular content publishers per category, then pull headlines from them.

### Step 1 — Discover Top Sites per Category

Use **Cloudflare Radar API** to get the top-ranked domains per category:
- API: `GET /radar/ranking/top?rankingType=popular&limit=50`
- Categories of interest: News & Media, Technology, Science, Finance, Politics
- Run periodically (weekly or monthly) to keep source list fresh

Also use **Cloudflare Radar `trending_rise`** to catch domains with sudden traffic spikes:
- API: `GET /radar/ranking/top?rankingType=trending_rise`
- Useful as a leading indicator — a domain spiking often means something happened

### Step 2 — Filter to Content Publishers

Many top sites are platforms, not content sources (Google, YouTube, Facebook, etc.).
Filter by Cloudflare category to keep only:
- News & Media
- Science & Technology blogs
- Finance / Business news

Exclude: Search Engines, Social Media Networks, Streaming, Ecommerce.

### Step 3 — Pull Headlines via RSS

For each publisher domain:
1. Auto-discover RSS feed (try `/feed`, `/rss`, `/atom.xml`, etc.)
2. Fetch latest headlines + summaries
3. Tag each item with source domain and category

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

1. **Source discovery** — Cloudflare Radar top sites per category → filter publishers → find RSS feeds
2. **Headline fetcher** — pull latest headlines from discovered RSS feeds, output ranked list
3. **Curation layer** — Claude scoring against interest profile
4. **Script generator** — Claude writes narration
5. **TTS** — ElevenLabs API
6. **Video assembly** — moviepy + Pexels b-roll
7. **Scheduler** — daily cron job
8. **Slack delivery** — post to channel

---

## Notes

- Cloudflare Radar API token available (free tier, `Read Cloudflare Radar data` permission)
- Reddit tool available at `/home/ubuntu/reddit-tool/`
- Validation tool (HN, Google Trends, Product Hunt, Reddit) at `/home/ubuntu/validation-tool/`
- Keep topic discovery modular — each source is a separate function
