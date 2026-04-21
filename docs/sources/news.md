# News Sources

Investigation based on [Similarweb Top News & Media Websites](https://www.similarweb.com/top-websites/news-and-media/) (March 2026), which measures actual human page visits. This is the most accurate signal for "what news sites people actually read."

Note: Non-English sources are included — Claude translates titles/summaries during the curation step.

---

## Top 50 News & Media Sites (Similarweb)

| # | Domain | Language | RSS Feed | Notes |
|---|---|---|---|---|
| 1 | yahoo.co.jp | Japanese | `https://news.yahoo.co.jp/rss/topics/top-picks.xml` | Aggregator |
| 2 | yahoo.com | English | `https://news.yahoo.com/rss` | Aggregator |
| 3 | globo.com | Portuguese | `https://feeds.feedburner.com/gg/noticias` | Brazil's largest media |
| 4 | news.yahoo.co.jp | Japanese | (same as yahoo.co.jp) | |
| 5 | nytimes.com | English | `https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml` | |
| 6 | bbc.com | English | `http://feeds.bbci.co.uk/news/rss.xml` | |
| 7 | bbc.co.uk | English | (duplicate of bbc.com) | Skip |
| 8 | cnn.com | English | `http://rss.cnn.com/rss/edition.rss` | |
| 9 | msn.com | English | `https://www.msn.com/en-us/news/rss` | Aggregator |
| 10 | qq.com | Chinese | `https://news.qq.com/rss/out.xml` | Tencent News |
| 11 | theguardian.com | English | `https://www.theguardian.com/world/rss` | |
| 12 | indiatimes.com | English | `https://timesofindia.indiatimes.com/rssfeedstopstories.cms` | India |
| 13 | douyin.com | Chinese | None | TikTok China — no RSS |
| 14 | news.google.com | Multi | `https://news.google.com/rss` | Best aggregator |
| 15 | foxnews.com | English | `https://moxie.foxnews.com/google-publisher/latest.xml` | |
| 16 | uol.com.br | Portuguese | `https://rss.uol.com.br/feed/noticias.xml` | Brazil |
| 17 | infobae.com | Spanish | `https://www.infobae.com/feeds/rss/` | Latin America |
| 18 | finance.yahoo.com | English | `https://finance.yahoo.com/news/rssindex` | Finance-focused |
| 19 | news.naver.com | Korean | `https://news.naver.com/rss/main.xml` | South Korea |
| 20 | dailymail.co.uk | English | `https://www.dailymail.co.uk/articles.rss` | UK tabloid |
| 21 | aljazeera.com | English | `https://www.aljazeera.com/xml/rss/all.xml` | Middle East focus |
| 22 | bild.de | German | `https://www.bild.de/rssfeeds/rss3-20745882,feed=alles.bild.html` | Germany |
| 23 | ndtv.com | English | `https://feeds.feedburner.com/ndtvnews-top-stories` | India |
| 24 | auone.jp | Japanese | None | Japan — no RSS |
| 25 | onet.pl | Polish | `https://wiadomosci.onet.pl/rss` | Poland |
| 26 | people.com | English | `https://people.com/feed/` | Entertainment/celeb |
| 27 | wp.pl | Polish | `https://rss.wp.pl/pub/rss/wiadomosci.xml` | Poland |
| 28 | substack.com | English | None | Platform — no single RSS |
| 29 | news.yahoo.com | English | (same as yahoo.com) | Skip |
| 30 | n-tv.de | German | `https://www.n-tv.de/rss` | Germany |
| 31 | aajtak.in | Hindi | `https://aajtak.intoday.in/rss/aajtaktop.xml` | India |
| 32 | fmkorea.com | Korean | None | Korea — no RSS |
| 33 | vnexpress.net | Vietnamese | `https://vnexpress.net/rss/tin-moi-nhat.rss` | Vietnam |
| 34 | livedoor.jp | Japanese | None | Japan — aggregator |
| 35 | hindustantimes.com | English | `https://www.hindustantimes.com/rss/topnews/rssfeed.xml` | India |
| 36 | detik.com | Indonesian | `https://rss.detik.com/index.php/detikcom` | Indonesia |
| 37 | interia.pl | Polish | `https://fakty.interia.pl/feed` | Poland |
| 38 | elpais.com | Spanish | `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada` | Spain |
| 39 | corriere.it | Italian | `https://xml2.corriereobjects.it/rss/homepage.xml` | Italy |
| 40 | repubblica.it | Italian | `https://www.repubblica.it/rss/homepage/rss2.0.xml` | Italy |
| 41 | cnbc.com | English | `https://feeds.nbcnews.com/nbcnews/public/news` | Finance/business |
| 42 | t-online.de | German | `https://www.t-online.de/feed.xml` | Germany |
| 43 | rbc.ru | Russian | `https://rss.rbcrn.ru/v1/main.rss` | Russia |
| 44 | usatoday.com | English | `https://rssfeeds.usatoday.com/usatoday-NewsTopStories` | |
| 45 | edition.cnn.com | English | (duplicate of cnn.com) | Skip |
| 46 | reuters.com | English | `https://feeds.reuters.com/reuters/topNews` | Wire service |
| 47 | elmundo.es | Spanish | `https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml` | Spain |
| 48 | news18.com | English | `https://www.news18.com/rss/india.xml` | India |
| 49 | apnews.com | English | `https://rsshub.app/apnews/topics/apf-topnews` | No official RSS; RSSHub proxy |
| 50 | nbcnews.com | English | `https://feeds.nbcnews.com/nbcnews/public/news` | |

---

## Trending Signals

Sources for engagement/trending signal, not article content.

| Source | Global Rank | API | Notes | Status |
|---|---|---|---|---|
| Google Trends | #1 | `https://trends.google.com/trends/api/dailytrends` | Search interest 0–100; no auth | Planned |
| X / Twitter | #6 | Twitter API v2 | Paid ($100/month minimum) | Keep in mind |
| Reddit | #7 | `r/news`, `r/worldnews`, `r/politics` hot posts | AWS IPs blocked; use `REDDIT_PROXY_URL` | Planned |
| Bing Trends | #8 | `https://www.bing.com/trends/api/dailytrends` | Unofficial, no auth | Planned |
| Wikipedia Pageviews | #10 | `https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{date}` | Most-read articles; strong breaking news signal | Planned |
| TikTok | #11 | None | No public trending API | N/A |
| Baidu | #18 | Baidu Index API | Chinese coverage; needs account | Keep in mind |
| Pinterest | #22 | Pinterest Trends API | Visual trends; needs app approval | Keep in mind |
| Snapchat | — | `https://trends.snap.com/api/v1/topicTrends` | No auth required; skews younger | Planned |
| Spotify | — | Spotify Web API — podcast charts | Needs OAuth; good for news podcasts | Keep in mind |

---

## Notes

- **Duplicates removed:** bbc.co.uk (#7), news.yahoo.co.jp (#4), news.yahoo.com (#29), edition.cnn.com (#45)
- **No RSS available:** douyin.com (#13), auone.jp (#24), fmkorea.com (#32), livedoor.jp (#34), substack.com (#28)
- **Translation:** Non-English titles/summaries are translated by Claude during the curation step
- **RSS feeds marked as approximate** — some may need verification before use
