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

Based on Similarweb global top 50. Every platform assessed for a usable trending API.

| Global Rank | Domain | Trending Signal | API | Status |
|---|---|---|---|---|
| #1 | google.com | Google Trends — search interest 0–100 | `https://trends.google.com/trends/api/dailytrends` — no auth | Planned |
| #2 | youtube.com | Trending videos | YouTube Data API — key in `.env` | ✅ `fetchers/youtube.py` |
| #3 | facebook.com | — | Trending shut down 2018; API restricted | N/A |
| #4 | instagram.com | — | No public trending API | N/A |
| #5 | chatgpt.com | — | No trending signal | N/A |
| #6 | x.com | Trending topics | Twitter API v2 — paid ($100/month) | Keep in mind |
| #7 | reddit.com | Hot posts (`r/news`, `r/worldnews`, `r/politics`) | AWS IPs blocked; use `REDDIT_PROXY_URL` | Planned |
| #8 | bing.com | Bing Trends — search interest | `https://www.bing.com/trends/api/dailytrends` — unofficial, no auth | Planned |
| #9 | whatsapp.com | — | Private messaging; no public signal | N/A |
| #10 | wikipedia.org | Most-read articles — strong breaking news signal | `https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{date}` — no auth | Planned |
| #11 | tiktok.com | — | No public trending API | N/A |
| #14 | yandex.ru | Yandex Trends | Yandex Wordstat API — Russia-focused | Keep in mind |
| #16 | amazon.com | Movers & Shakers / Best Sellers | `https://www.amazon.com/gp/movers-and-shakers` — scrapeable | Keep in mind |
| #18 | baidu.com | Baidu Hot Search | Baidu Index API — China-focused; needs account | Keep in mind |
| #21 | netflix.com | Netflix Top 10 charts | `https://www.netflix.com/tudum/top10` — unofficial JSON | Keep in mind |
| #22 | pinterest.com | Pinterest Trends | Pinterest Trends API — needs app approval | Keep in mind |
| #26 | bilibili.com | Trending videos | `https://api.bilibili.com/x/web-interface/ranking/v2` — no auth; China-focused | Keep in mind |
| #33 | twitch.tv | Trending streams/games | Twitch API — free, needs client ID | Keep in mind |
| #38 | spotify.com | Podcast & music charts | Spotify Web API — needs OAuth | Keep in mind |
| #42 | t.me | Telegram public channels | No official trending API | N/A |
| #44 | duckduckgo.com | — | Privacy-focused; no trends by design | N/A |
| #48 | github.com | Trending repos | HTML scrape | ✅ `fetchers/github.py` |

---

## Notes

- **Duplicates removed:** bbc.co.uk (#7), news.yahoo.co.jp (#4), news.yahoo.com (#29), edition.cnn.com (#45)
- **No RSS available:** douyin.com (#13), auone.jp (#24), fmkorea.com (#32), livedoor.jp (#34), substack.com (#28)
- **Translation:** Non-English titles/summaries are translated by Claude during the curation step
- **RSS feeds marked as approximate** — some may need verification before use
