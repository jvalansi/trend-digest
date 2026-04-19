# Tech Sources

Investigation based on the Stack Overflow 2025 Developer Survey (65k+ respondents).

---

## Platform Usage & API Availability

| Platform | Developer Usage | API | Status |
|---|---|---|---|
| Stack Overflow | 84% | ✅ Public API, no auth | Not yet fetched |
| GitHub | 67% | ✅ Public API, no auth | ✅ `fetchers/github.py` |
| YouTube | 61% | ✅ API key configured | ✅ `fetchers/youtube.py` |
| Reddit | 54% | ⚠️ AWS IPs blocked; needs proxy or credentials | Pending |
| Stack Exchange | 47% | ✅ Same API as Stack Overflow | Not yet fetched |
| Discord | 39% | ⚠️ API is for server bots, not public content feeds | N/A |
| LinkedIn | 37% | ❌ Very restricted | N/A |
| Medium | 29% | ❌ No public API | N/A |
| Hacker News | 20% | ✅ Free, no auth — Firebase REST API | ✅ `fetchers/hn.py` |
| X / Twitter | 17% | ⚠️ API available but expensive | Pending |
| Slack (public) | 16% | ❌ No public content API | N/A |
| Dev.to | 11% | ✅ Free public API, no auth | Not yet fetched |
| Bluesky | 11% | ✅ AT Protocol, no auth for public feeds | Not yet fetched |
| Twitch | 9% | ⚠️ API exists but not relevant for tech news | N/A |
| Substack | 7% | ⚠️ No official API; RSS feeds available per publication | N/A |

Key insight: YouTube and Reddit both significantly outrank Hacker News among developers. HN is high-quality but niche (~20%).

### Reddit notes
Reddit blocks requests from cloud/AWS IPs regardless of auth method.
The `.env` includes a `REDDIT_PROXY_URL` (webshare.io residential proxy) that may bypass this.
PRAW-based tool at `/home/ubuntu/reddit-tool/` — needs `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` once approved.

---

## RSS Feeds (implemented in `fetchers/rss.py`)

| Source | Feed |
|---|---|
| The Verge | `https://www.theverge.com/rss/index.xml` |
| TechCrunch | `https://techcrunch.com/feed/` |
| Ars Technica | `https://feeds.arstechnica.com/arstechnica/index` |
| Wired | `https://www.wired.com/feed/rss` |
| MIT Tech Review | `https://www.technologyreview.com/feed/` |
| VentureBeat | `https://venturebeat.com/feed/` |
| Engadget | `https://www.engadget.com/rss.xml` |
| ZDNet | `https://www.zdnet.com/news/rss.xml` |

## YouTube Channels (implemented in `fetchers/youtube.py`)

| Channel | ID |
|---|---|
| Fireship | `UCsBjURrPoezykLs9EqgamOA` |
| Linus Tech Tips | `UCXuqSBlHAE6Xw-yeJA0Tunw` |
| Theo (t3.gg) | `UCbmNph6atAoGfqLoCL_duAg` |
| freeCodeCamp | `UC8butISFwT-Wl7EV0hUK0BQ` |
| ThePrimeagen | `UCddiUEpeqJcYeBxX1IVBKvQ` |
| ByteByteGo | `UCo8bcnLyZH8tBIH9V1mLgqQ` |

## Reddit Subreddits (pending)

`r/technology`, `r/programming`, `r/webdev`, `r/compsci`
