# News Sources

Investigation based on the [Wikipedia List of Most-Visited Websites](https://en.wikipedia.org/wiki/List_of_most-visited_websites) (Similarweb, March 2026), which measures actual human page visits. Cloudflare Radar (DNS query volume) was considered but rejected — it inflates infrastructure/CDN domains and is not representative of human traffic.

---

## Most-Visited Websites (Top 50, Similarweb March 2026)

Full list for reference. News/media relevant entries highlighted.

| Rank | Domain | Site |
|---|---|---|
| 1 | google.com | Google Search |
| 2 | youtube.com | YouTube |
| 3 | facebook.com | Facebook |
| 4 | instagram.com | Instagram |
| 5 | chatgpt.com | ChatGPT |
| **6** | **x.com** | **X / Twitter** |
| **7** | **reddit.com** | **Reddit** |
| 8 | bing.com | Microsoft Bing |
| 9 | whatsapp.com | WhatsApp |
| **10** | **wikipedia.org** | **Wikipedia** |
| 11 | tiktok.com | TikTok |
| 12 | yahoo.co.jp | Yahoo Japan |
| **13** | **yahoo.com** | **Yahoo!** |
| 14 | yandex.ru | Yandex |
| 15 | gemini.google.com | Google Gemini |
| 16 | amazon.com | Amazon |
| 17 | linkedin.com | LinkedIn |
| **18** | **baidu.com** | **Baidu** |
| 19 | bet.br | BET.br |
| 20 | naver.com | Naver |
| 21 | netflix.com | Netflix |
| 22 | pinterest.com | Pinterest |
| 23 | live.com | Microsoft Live |
| 25 | dzen.ru | Dzen News (Russia) |
| 26 | bilibili.com | Bilibili (China) |
| 33 | twitch.tv | Twitch |
| **35** | **weather.com** | **The Weather Channel** |
| 36 | vk.com | VK (Russia) |
| **37** | **globo.com** | **Globo (Brazil)** |
| **39** | **news.yahoo.co.jp** | **Yahoo! News Japan** |
| **43** | **nytimes.com** | **The New York Times** |

---

## News RSS Sources

Selected from the most-visited list, filtered for original news reporting with working RSS feeds.

| Rank | Domain | RSS Feed | Notes |
|---|---|---|---|
| 1 | google.com | `https://news.google.com/rss` | Google News — aggregates top stories across all publishers |
| 13 | yahoo.com | `https://news.yahoo.com/rss` | Aggregator; high traffic |
| 43 | nytimes.com | `https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml` | |
| — | cnn.com | `http://rss.cnn.com/rss/edition.rss` | Top 1,000 Cloudflare |
| — | bbc.com | `http://feeds.bbci.co.uk/news/rss.xml` | Top 2,000 Cloudflare |
| — | reuters.com | `https://feeds.reuters.com/reuters/topNews` | Wire service |
| — | theguardian.com | `https://www.theguardian.com/world/rss` | |
| — | washingtonpost.com | `https://feeds.washingtonpost.com/rss/world` | |
| — | bloomberg.com | `https://feeds.bloomberg.com/markets/news.rss` | |
| — | apnews.com | `https://rsshub.app/apnews/topics/apf-topnews` | No official RSS; RSSHub proxy |
| — | foxnews.com | `https://moxie.foxnews.com/google-publisher/latest.xml` | |
| — | wsj.com | `https://feeds.a.dj.com/rss/RSSWorldNews.xml` | Paywalled; summaries come through |

---

## Trending Signals

Sources for engagement/trending signal, not article content.

| Source | Rank | API | Notes | Status |
|---|---|---|---|---|
| Google Trends | #1 | `https://trends.google.com/trends/api/dailytrends` | Search interest 0–100; no auth | Planned |
| X / Twitter | #6 | Twitter API v2 | Paid ($100/month minimum) | Keep in mind |
| Reddit | #7 | `r/news`, `r/worldnews`, `r/politics` hot posts | AWS IPs blocked; use `REDDIT_PROXY_URL` from `.env` | Planned |
| Bing Trends | #8 | `https://www.bing.com/trends/api/dailytrends` | Unofficial, no auth | Planned |
| Wikipedia Pageviews | #10 | `https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{date}` | Most-read articles; strong breaking news signal | Planned |
| TikTok | #11 | None | No public trending API | N/A |
| Baidu | #18 | Baidu Index API | Chinese coverage; needs account | Keep in mind |
| Pinterest | #22 | Pinterest Trends API | Visual trends; needs app approval | Keep in mind |
| Snapchat | — | `https://trends.snap.com/api/v1/topicTrends` | No auth required; skews younger | Planned |
| Spotify | — | Spotify Web API — podcast charts | Needs OAuth; good for news podcasts | Keep in mind |

---

## Notable Platforms — API Status

| Platform | Rank | News Relevance | API Access |
|---|---|---|---|
| YouTube | #2 | News channels, trending videos | ✅ Already in `fetchers/youtube.py` |
| Facebook | #3 | News sharing | ❌ Trending shut down 2018; API restricted |
| Instagram | #4 | Visual news | ❌ No public trending API |
| LinkedIn | #17 | Business/professional news | ❌ Very restricted |
| TikTok | #11 | Trending topics | ❌ No public API |
| Globo | #37 | Brazilian news (Portuguese) | ✅ RSS available |
| Yandex | #14 | Russian news | ⚠️ Restricted outside Russia |
