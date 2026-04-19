# Tech Sources

Investigation based on the Stack Overflow 2025 Developer Survey (65k+ respondents).

---

## Platform Usage & API Availability

| Platform | Developer Usage | API |
|---|---|---|
| Stack Overflow | 84% | ✅ Public API, no auth |
| GitHub | 67% | ✅ Public API, no auth |
| YouTube | 61% | ✅ API key configured |
| Reddit | 54% | ⚠️ AWS IPs blocked; needs proxy or credentials |
| Stack Exchange | 47% | ✅ Same API as Stack Overflow |
| Discord | 39% | ⚠️ API is for server bots, not public content feeds |
| LinkedIn | 37% | ❌ Very restricted |
| Medium | 29% | ❌ No public API |
| Hacker News | 20% | ✅ Free, no auth — Firebase REST API |
| X / Twitter | 17% | ⚠️ API available but expensive |
| Slack (public) | 16% | ❌ No public content API |
| Dev.to | 11% | ✅ Free public API, no auth |
| Bluesky | 11% | ✅ AT Protocol, no auth for public feeds |
| Twitch | 9% | ⚠️ API exists but not relevant for tech news |
| Substack | 7% | ⚠️ No official API; RSS feeds available per publication |

Key insight: YouTube and Reddit both significantly outrank Hacker News among developers. HN is high-quality but niche (~20%).

### Reddit notes
Reddit blocks requests from cloud/AWS IPs regardless of auth method.
The `.env` includes a `REDDIT_PROXY_URL` (webshare.io residential proxy) that may bypass this.
PRAW-based tool at `/home/ubuntu/reddit-tool/` — needs `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` once approved.

---

## RSS Feeds

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

## Reddit Subreddits

`r/technology`, `r/programming`, `r/webdev`, `r/compsci`
