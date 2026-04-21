# News Sources

Investigation based on Cloudflare Radar top 100 global domains (by DNS traffic, April 2026), supplemented by domain-level bucket rankings for known news sites.

---

## News & Media in the Global Top 100

Only 3 domains in the top 100 are categorized as "News & Media":

| Rank | Domain | Notes |
|---|---|---|
| #34 | yahoo.com | Aggregator, not original reporting |
| #46 | msn.com | Aggregator, not original reporting |
| #95 | qq.com | Chinese platform (Tencent) |

Major news publishers (CNN, NYT, BBC, etc.) appear in the top 1,000–5,000 but Cloudflare only gives bucket-level precision below rank 100.

---

## News RSS Sources

Ranked by Cloudflare bucket. Within each bucket, order is not significant.

| Bucket | Domain | RSS Feed | Notes |
|---|---|---|---|
| Top 100 | google.com | `https://news.google.com/rss` | Aggregates top stories across all publishers |
| Top 1,000 | cnn.com | `http://rss.cnn.com/rss/edition.rss` | |
| Top 1,000 | foxnews.com | `https://moxie.foxnews.com/google-publisher/latest.xml` | |
| Top 1,000 | nytimes.com | `https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml` | |
| Top 2,000 | bbc.com | `http://feeds.bbci.co.uk/news/rss.xml` | |
| Top 2,000 | wsj.com | `https://feeds.a.dj.com/rss/RSSWorldNews.xml` | Paywalled articles; summaries come through |
| Top 5,000 | reuters.com | `https://feeds.reuters.com/reuters/topNews` | Wire service, high volume |
| Top 5,000 | theguardian.com | `https://www.theguardian.com/world/rss` | |
| Top 5,000 | washingtonpost.com | `https://feeds.washingtonpost.com/rss/world` | |
| Top 5,000 | bloomberg.com | `https://feeds.bloomberg.com/markets/news.rss` | |
| Top 5,000 | apnews.com | `https://rsshub.app/apnews/topics/apf-topnews` | No official RSS; RSSHub proxy |

---

## Trending Signals

Sources for engagement/trending signal, not article content.

| Source | API | Notes | Status |
|---|---|---|---|
| Google Trends | `https://trends.google.com/trends/api/dailytrends` | Search interest score 0–100; no auth | Planned: `fetchers/trends_google.py` |
| Bing Trends | `https://www.bing.com/trends/api/dailytrends` | Unofficial but works without auth | Planned: `fetchers/trends_bing.py` |
| Snapchat Trends | `https://trends.snap.com/api/v1/topicTrends` | No auth required; skews younger demographic | Planned |
| Wikipedia Pageviews | `https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{date}` | Most-read articles; strong breaking news signal | Planned |
| Spotify | Spotify Web API — podcast charts | Needs OAuth; good for news podcast signal (NPR, BBC, NYT The Daily) | Keep in mind |
| Baidu | Baidu Index API | Chinese coverage; needs account | Keep in mind |
| Pinterest | Pinterest Trends API | Visual trends; needs app approval | Keep in mind |

---

## Notable Non-News Domains in Top 100

For reference — domains explored during source selection that are not news but potentially relevant:

| Domain | Rank | Reason noted |
|---|---|---|
| youtube.com | #15 | Already in `fetchers/youtube.py` |
| wikipedia.org | #51 | Reference/context; pageviews used as trending signal |
| spotify.com | #38 | Podcast charts as news signal (future) |
| baidu.com | #49 | Chinese search/news (future) |
| snapchat.com | #61 | Trends API available |
| pinterest.com | #93 | Trends API available |
| linkedin.com | #68 | API too restricted for content access |
| tiktokv.com | #31 | No public trending API |
