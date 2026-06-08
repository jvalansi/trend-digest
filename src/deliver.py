#!/usr/bin/env python3
"""
Delivery — formats aggregated items and posts to Slack.

Usage:
  python aggregate.py | python deliver.py
  python deliver.py --input FILE
  python deliver.py --input FILE --dry-run
"""

import argparse
import html as html_module
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

SLACK_CHANNEL = os.environ.get("TREND_DIGEST_CHANNEL", "proj-trend-digest")
SCIENCE_CHANNEL = os.environ.get("SCIENCE_DIGEST_CHANNEL", SLACK_CHANNEL)
NEWS_CHANNEL = os.environ.get("NEWS_DIGEST_CHANNEL", "proj-news-digest")
FINANCE_CHANNEL = os.environ.get("FINANCE_DIGEST_CHANNEL", SLACK_CHANNEL)
CLAUDE_PATH = os.environ.get("CLAUDE_PATH", "/home/ubuntu/.local/bin/claude")

_SEEN_ITEMS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seen_items.json")


def load_seen_items() -> dict:
    try:
        with open(_SEEN_ITEMS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_seen_items(seen: dict) -> None:
    with open(_SEEN_ITEMS_PATH, "w") as f:
        json.dump(seen, f, indent=2)


def annotate_seen(items: list[dict], seen: dict) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    for item in items:
        url = item.get("url", "")
        if url in seen:
            first = seen[url]["first_seen"]
            try:
                delta = (datetime.now(timezone.utc).date() - datetime.fromisoformat(first).date()).days
            except Exception:
                delta = 0
            if delta > 0:
                item["days_since_first_seen"] = delta


def update_seen(items: list[dict], seen: dict) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    for item in items:
        url = item.get("url", "")
        if not url:
            continue
        if url in seen:
            seen[url]["count"] += 1
            seen[url]["last_seen"] = today
        else:
            seen[url] = {"first_seen": today, "last_seen": today, "count": 1}

REDDIT_SUBREDDITS = {
    "tech": ["artificial", "MachineLearning", "programming", "technology"],
    "news": ["worldnews", "geopolitics"],
    "finance": ["investing", "stocks", "economics"],
}


SOURCE_URLS = {
    "The Verge": "https://www.theverge.com",
    "TechCrunch": "https://techcrunch.com",
    "Ars Technica": "https://arstechnica.com",
    "Wired": "https://www.wired.com",
    "MIT Tech Review": "https://www.technologyreview.com",
    "VentureBeat": "https://venturebeat.com",
    "Engadget": "https://www.engadget.com",
    "ZDNet": "https://www.zdnet.com",
    "Hacker News": "https://news.ycombinator.com",
    "GitHub Blog": "https://github.blog",
    "Nature": "https://www.nature.com",
    "Science": "https://www.science.org",
    "New Scientist": "https://www.newscientist.com",
    "Scientific American": "https://www.scientificamerican.com",
    "BBC News": "https://www.bbc.com/news",
    "New York Times": "https://www.nytimes.com",
    "The Guardian": "https://www.theguardian.com",
    "Reuters": "https://www.reuters.com",
    "CNN": "https://www.cnn.com",
    "Yahoo Finance": "https://finance.yahoo.com",
    "MarketWatch": "https://www.marketwatch.com",
    "Bloomberg": "https://www.bloomberg.com",
    "Financial Times": "https://www.ft.com",
}


def _youtube_thumbnail(url: str) -> str | None:
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if m:
        return f"https://img.youtube.com/vi/{m.group(1)}/hqdefault.jpg"
    return None


def fetch_og_image(url: str, timeout: float = 4.0) -> str | None:
    thumb = _youtube_thumbnail(url)
    if thumb:
        return thumb
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            chunk = resp.read(65536).decode("utf-8", errors="ignore")
        for pattern in [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        ]:
            m = re.search(pattern, chunk)
            if m:
                img_url = m.group(1)
                if img_url.startswith("http://") or img_url.startswith("https://"):
                    return img_url
    except Exception:
        pass
    return None


_SOURCE_IMAGES = {
    "Reddit":             "https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png",
    "Reddit Science":     "https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png",
    "Reddit Tech":        "https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png",
    "Reddit Finance":     "https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png",
    "Reddit News":        "https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png",
    "Semantic Scholar":   "https://www.semanticscholar.org/img/semantic_scholar_og.png",
    "New Scientist":      "https://www.newscientist.com/build/images/meta/new-scientist-social-meta-image.85ef6f47.png",
    "Scientific American":"https://www.scientificamerican.com/static/sciam-mark.jpg",
    "HF Papers":          "https://huggingface.co/front/assets/huggingface_logo.svg",
    "HF Models":          "https://huggingface.co/front/assets/huggingface_logo.svg",
}

_SOURCE_DOMAINS = {
    "bioRxiv": "biorxiv.org",
    "medRxiv": "medrxiv.org",
    "Nature": "nature.com",
    "Science": "science.org",
    "Ars Technica": "arstechnica.com",
    "Ars Technica Science": "arstechnica.com",
    "MIT Tech Review": "technologyreview.com",
    "Hacker News": "news.ycombinator.com",
    "Altmetric": "crossref.org",
    "TechCrunch": "techcrunch.com",
    "The Verge": "theverge.com",
    "Wired": "wired.com",
    "VentureBeat": "venturebeat.com",
    "Engadget": "engadget.com",
    "ZDNet": "zdnet.com",
    "GitHub Trending": "github.com",
    "YouTube Tech": "youtube.com",
    "YouTube News": "youtube.com",
}


def _source_fallback_image(source: str, url: str) -> str | None:
    """Return a fallback image for a source when OG scraping fails."""
    if source in _SOURCE_IMAGES:
        return _SOURCE_IMAGES[source]
    domain = _SOURCE_DOMAINS.get(source)
    if not domain:
        m = re.search(r'https?://(?:www\.)?([^/]+)', url)
        domain = m.group(1) if m else None
    if domain:
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
    return None


_PEXELS_CACHE: dict[str, str | None] = {}
_PEXELS_LAST_CALL = 0.0
_PEXELS_MIN_INTERVAL = 0.25  # 4 req/s well under free-tier limit


# Maps sets of title substrings → a Pexels-friendly search query
_SCIENCE_DOMAIN_MAP = [
    (["retina", "optic", "cornea", "ocular", "ophth", "vision"],        "eye retina closeup"),
    (["brain", "neuro", "cortex", "hippocamp", "cerebr", "synap", "axon", "neuron", "prefrontal", "amygdala", "affective"],
                                                                         "brain neuroscience"),
    (["cancer", "tumor", "carcinoma", "oncol", "malignant", "metasta",  "radioth"], "cancer research microscope"),
    (["immune", "antibod", "lymph", "monocyte", "macrophage", "cytokine", "chemokine", "t-cell", "immunol"], "immune cells blood"),
    (["genome", "dna", "gene", "rna", "crispr", "sequenc", "genomic", "transcript", "epigenet"], "dna genetics laboratory"),
    (["climate", "carbon", "emission", "warming", "atmospher", "arctic", "glacier"], "climate change earth"),
    (["quantum", "photon", "laser", "electron", "particle", "atomic", "plasma"],     "physics laboratory"),
    (["protein", "enzyme", "metabol", "biochem", "peptide", "amino"],    "molecular biology"),
    (["microbiome", "bacteria", "virus", "pathogen", "infect", "antibiotic"], "bacteria microscope"),
    (["mental health", "psychiatr", "depress", "anxiety", "cognit", "behavior"],    "mental health brain"),
    (["cardiovasc", "cardiac", "heart", "arterial", "blood pressure"],   "heart cardiology"),
    (["stem cell", "embryo", "differenti", "pluripotent"],               "stem cells research"),
    (["vaccine", "immuniz", "clinical trial", "therapeut"],              "vaccine medicine"),
    (["ecolog", "biodiversity", "species", "habitat", "ecosyst"],        "nature biodiversity"),
    (["space", "stellar", "galaxy", "planet", "orbit", "astrono"],       "space galaxy"),
    (["machine learning", "neural network", "deep learning", "artific"], "artificial intelligence technology"),
]

_NEWS_DOMAIN_MAP = [
    (["soccer", "football", "fifa", "world cup", "goal", "league", "champion", "match", "penalty", "striker"], "soccer football sports"),
    (["basketball", "nba", "wnba", "three-pointer", "dunk"], "basketball court game"),
    (["tennis", "wimbledon", "french open", "us open", "australian open", "grand slam", "serve", "forehand"], "tennis match court"),
    (["baseball", "mlb", "pitcher", "home run", "yankees", "dodgers", "cubs"], "baseball game stadium"),
    (["hockey", "nhl", "ice hockey", "stanley cup"], "ice hockey game"),
    (["ukraine", "russia", "war", "military", "troops", "missile", "zelenskyy", "putin", "kyiv", "nato", "invasion"], "war conflict military"),
    (["election", "vote", "ballot", "president", "congress", "senate", "democrat", "republican", "campaign", "polling"], "election voting politics"),
    (["music", "album", "singer", "rapper", "concert", "grammy", "billboard", "swift", "beyonce", "pop"], "music concert stage"),
    (["movie", "film", "actor", "actress", "oscars", "cinema", "box office", "marvel", "disney", "netflix"], "cinema movie theater"),
    (["trial", "court", "judge", "verdict", "lawsuit", "arrested", "charged", "stabbed", "murder", "crime", "shooting"], "courthouse law justice"),
    (["stock", "market", "economy", "inflation", "recession", "fed", "bitcoin", "crypto", "gdp", "trading"], "financial market charts"),
    (["earthquake", "hurricane", "flood", "storm", "wildfire", "disaster", "tornado", "tsunami"], "natural disaster emergency"),
    (["artificial intelligence", "chatgpt", "openai", "llm", "gemini", "tech company", "startup", "silicon valley"], "artificial intelligence technology"),
    (["space", "nasa", "rocket", "satellite", "astronaut", "mars", "moon", "launch", "orbit"], "space rocket launch"),
    (["iran", "nuclear", "deal", "sanction", "middle east", "israel", "hamas", "hezbollah", "beirut"], "middle east diplomacy"),
    (["trump", "biden", "white house", "executive order", "administration", "oval office", "secretary"], "white house government"),
    (["privacy", "data breach", "surveillance", "fcc", "regulation", "cybersecurity", "hack"], "technology security privacy"),
    (["immigration", "border", "migrant", "asylum", "deportation", "visa"], "border crossing immigration"),
    (["climate", "carbon", "emission", "green energy", "solar", "wind power", "fossil fuel"], "climate change environment"),
]


def _extract_keywords(item: dict) -> str:
    """Map a paper title to a Pexels-friendly search query."""
    text = (item.get("title", "") + " " + (item.get("summary") or "")[:300]).lower()
    for patterns, query in _SCIENCE_DOMAIN_MAP:
        if any(p in text for p in patterns):
            return query
    # Generic fallback: pick the 2 longest meaningful words from the title
    skip = {"study", "research", "analysis", "novel", "using", "based", "role",
            "effect", "impact", "review", "data", "model", "results", "method",
            "human", "associated", "potential", "increased", "decreased", "between"}
    words = [w for w in re.findall(r'\b[a-zA-Z]{5,}\b', item.get("title", "").lower()) if w not in skip]
    return " ".join(words[:2]) if words else item.get("title", "")[:40]


def _extract_keywords_news(item: dict) -> str:
    """Map a news/trend item to a Pexels-friendly search query."""
    text = (item.get("title", "") + " " + (item.get("summary") or "")[:300]).lower()
    for patterns, query in _NEWS_DOMAIN_MAP:
        if any(p in text for p in patterns):
            return query
    # Generic fallback: pick 2-3 meaningful words from title + summary
    skip = {"says", "amid", "after", "over", "with", "what", "from", "about", "latest",
            "update", "breaking", "report", "shows", "could", "would", "should", "their",
            "have", "been", "that", "this", "also", "more", "than", "will", "were"}
    words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', text) if w not in skip][:3]
    return " ".join(words) if words else item.get("title", "")[:40]


def _pexels_search(query: str, api_key: str) -> str | None:
    global _PEXELS_LAST_CALL
    if query in _PEXELS_CACHE:
        return _PEXELS_CACHE[query]

    # Rate-limit
    wait = _PEXELS_MIN_INTERVAL - (time.time() - _PEXELS_LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    _PEXELS_LAST_CALL = time.time()

    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode({
        "query": query, "per_page": 1, "orientation": "landscape",
    })
    try:
        req = urllib.request.Request(url, headers={"Authorization": api_key, "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        photos = data.get("photos", [])
        img = photos[0]["src"]["large"] if photos else None
    except Exception:
        img = None

    _PEXELS_CACHE[query] = img
    return img


# Sources that always return a generic site logo as og:image — skip OG fetch, go straight to Pexels
_SKIP_OG_SOURCES = {"medRxiv", "bioRxiv", "Semantic Scholar", "Altmetric"}


def fetch_og_images(items: list[dict]) -> dict[str, str | None]:
    """Concurrently fetch og:image; fall back to Pexels search or source logo."""
    pexels_key = os.environ.get("PEXELS_API_KEY")
    results: dict[str, str | None] = {}

    og_items = [item for item in items if item.get("source") not in _SKIP_OG_SOURCES]
    with ThreadPoolExecutor(max_workers=10) as ex:
        future_to_item = {ex.submit(fetch_og_image, item.get("article_url") or item["url"]): item for item in og_items}
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            url = item["url"]
            results[url] = future.result()

    _PEXELS_SCIENCE_SOURCES = {
        "bioRxiv", "medRxiv", "Semantic Scholar", "Altmetric",
        "Nature", "Science", "New Scientist", "Scientific American",
        "Ars Technica Science", "MIT Tech Review",
    }
    _PEXELS_NEWS_SOURCES = {"Google Trends", "Google Trends Global"}

    # Second pass: fill in missing images
    for item in items:
        url = item["url"]
        if results.get(url):
            continue
        source = item.get("source", "")
        if pexels_key and source in _PEXELS_SCIENCE_SOURCES:
            query = _extract_keywords(item)
            img = _pexels_search(query, pexels_key)
            results[url] = img or _source_fallback_image(source, url)
        elif pexels_key and source in _PEXELS_NEWS_SOURCES:
            query = _extract_keywords_news(item)
            img = _pexels_search(query, pexels_key)
            results[url] = img or _source_fallback_image(source, url)
        else:
            results[url] = _source_fallback_image(source, url)

    return results


def _format_sources_html(sources: list[str]) -> str:
    parts = []
    for s in sources:
        url = SOURCE_URLS.get(s)
        if url:
            parts.append(f'<a href="{html_module.escape(url)}">{html_module.escape(s)}</a>')
        else:
            parts.append(html_module.escape(s))
    return " · ".join(parts)


def _entry_html(title: str, url: str, desc: str, sources: list[str], og_image: str | None) -> str:
    t = html_module.escape(title)
    d = html_module.escape(desc) if desc else ""
    u = html_module.escape(url)
    s_html = " · ".join(f'<a href="{u}">{html_module.escape(s)}</a>' for s in (sources or ["Source"]))
    img = f'<figure><img src="{html_module.escape(og_image)}" /></figure>\n' if og_image else ""
    return (
        f'{img}<h4>{t}</h4>\n'
        + (f"<p>{d}</p>\n" if d else "")
        + f"<p><em>{s_html}</em></p>\n"
    )


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def format_as_html(label: str, date_str: str, items: list[dict], descriptions: list[str], sections: dict, section_descs: list[str], og_images: dict[str, str | None] | None = None) -> str:
    """Format digest items as an HTML document for Medium publishing."""
    og_images = og_images or {}

    all_sections = [("top-stories", "Top Stories")] + [(_slugify(name), name) for name in sections]

    toc = "<ul>\n" + "".join(f'<li><a href="#{slug}">{html_module.escape(name)}</a></li>\n' for slug, name in all_sections) + "</ul>\n"

    parts = [
        f"<h1>{html_module.escape(label)} — {html_module.escape(date_str)}</h1>\n",
        f"<p>Your daily roundup of the most important stories in tech, science, and AI.</p>\n",
        toc,
        f'<hr>\n<h2 id="top-stories">Top Stories</h2>\n',
    ]
    for item, desc in zip(items, descriptions):
        title = item.get("title_en") or item["title"]
        url = item["url"]
        sources = item.get("sources", [item["source"]])
        parts.append(_entry_html(title, url, desc, sources, og_images.get(url)))
    desc_idx = 0
    for name, sitems in sections.items():
        slug = _slugify(name)
        parts.append(f'<hr>\n<h2 id="{slug}">{html_module.escape(name)}</h2>\n')
        for item in sitems:
            title = item.get("title_en") or item["title"]
            url = item["url"]
            sources = item.get("sources", [item["source"]])
            desc = section_descs[desc_idx] if desc_idx < len(section_descs) else ""
            desc_idx += 1
            parts.append(_entry_html(title, url, desc, sources, og_images.get(url)))
    return "".join(parts)


def generate_social_teaser(items: list[dict], label: str) -> str:
    """Ask Claude to write a 2-sentence social media teaser for the digest."""
    top = [{"title": item.get("title_en") or item["title"]} for item in items[:5]]
    prompt = (
        f"Write a 2-sentence social media post teasing today's {label}. "
        "Be specific, mention 1-2 topics, and end with a hook. "
        "Plain text only, no hashtags, no emojis, no quotes.\n\n"
        f"Top stories: {json.dumps(top, ensure_ascii=False)}"
    )
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    result = subprocess.run(
        [CLAUDE_PATH, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        return f"Today's {label} is live."
    return json.loads(result.stdout).get("result", "").strip()


def generate_descriptions(items: list[dict], mode: str = "tech") -> list[str]:
    """Ask Claude to write a one-sentence description for each item."""
    compact = [
        {
            "index": i,
            "title": item.get("title_en") or item["title"],
            "summary": item.get("summary", "")[:300],
        }
        for i, item in enumerate(items)
    ]
    if mode == "finance":
        instruction = (
            "Write a single plain-text sentence (max 30 words) describing each ETF/financial item below. "
            "For ETFs that track a specific asset, index, or company, briefly explain what that underlying is "
            "(e.g. what the company does, what the index measures). Be specific and factual. "
            "Return ONLY a JSON array of objects with 'index' and 'description' fields."
        )
    else:
        instruction = (
            "Write a single plain-text sentence (max 20 words) describing each news item below. "
            "Be specific and factual. Return ONLY a JSON array of objects with 'index' and 'description' fields."
        )
    prompt = instruction + "\n\n" + json.dumps(compact, ensure_ascii=False)
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    result = subprocess.run(
        [CLAUDE_PATH, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        return [""] * len(items)
    response_text = json.loads(result.stdout).get("result", "")
    start, end = response_text.find("["), response_text.rfind("]") + 1
    descs = json.loads(response_text[start:end])
    desc_map = {d["index"]: d["description"] for d in descs}
    return [desc_map.get(i, "") for i in range(len(items))]


def format_item_telegram(item: dict, description: str) -> str:
    title = item.get("title_en") or item["title"]
    url = item["url"]
    sources = item.get("sources", [item["source"]])
    source_str = " · ".join(sources)
    desc_str = f"\n  {description}" if description else ""
    days = item.get("days_since_first_seen")
    seen_str = f" · ↩ {days}d" if days else ""
    return f"• [{title}]({url}){desc_str}\n  _{source_str}{seen_str}_"


def post_to_telegram(text: str) -> None:
    proc = subprocess.run(
        ["cc-connect", "send", "--stdin"],
        input=text, text=True, capture_output=True,
    )
    if proc.returncode != 0:
        print(f"cc-connect error: {proc.stderr}", file=sys.stderr)
        raise RuntimeError("cc-connect send failed")


def format_item(item: dict, description: str) -> str:
    sources = item.get("sources", [item["source"]])
    source_str = " · ".join(sources)
    title = item.get("title_en") or item["title"]
    url = item["url"]
    desc_str = f"\n   {description}" if description else ""
    raw = item.get("engagement_raw")
    eng = item.get("engagement")
    engagement_str = ""
    if raw is not None and eng is not None:
        engagement_str = f" · {int(raw)} pts · z={eng:+.2f}"
    days = item.get("days_since_first_seen")
    seen_str = f" · ↩ {days}d" if days else ""
    return f"*<{url}|{title}>*{desc_str}\n   _{source_str}{engagement_str}{seen_str}_"


def post_to_slack(text: str, token: str, channel: str, thread_ts: str | None = None, unfurl: bool = False, attachments: list | None = None) -> str:
    """Post a message and return its ts."""
    body: dict = {"channel": channel, "text": text, "unfurl_links": unfurl, "unfurl_media": unfurl}
    if thread_ts:
        body["thread_ts"] = thread_ts
    if attachments:
        body["attachments"] = attachments
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        print(f"Slack error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)
    return result["ts"]


def _publish_to_socials(label, date_str, rss_items, rss_descs, sections, section_descs, mode):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from publishers import medium, bluesky, linkedin, reddit

    all_items = rss_items + [item for items in sections.values() for item in items]
    title = f"{label} — {date_str}"
    print("Fetching OG images...", file=sys.stderr)
    og_images = fetch_og_images(all_items)
    fetched = sum(1 for v in og_images.values() if v)
    print(f"  Got {fetched}/{len(all_items)} images", file=sys.stderr)
    content_html = format_as_html(label, date_str, rss_items, rss_descs, sections, section_descs, og_images)
    teaser = generate_social_teaser(all_items, label)

    medium_token = os.environ.get("MEDIUM_TOKEN")
    post_url = None
    if medium_token:
        try:
            post_url = medium.publish(title, content_html, medium_token)
            print(f"Published to Medium: {post_url}", file=sys.stderr)
        except Exception as e:
            print(f"Medium publish failed: {e}", file=sys.stderr)
    else:
        print("MEDIUM_TOKEN not set — skipping Medium", file=sys.stderr)

    if not post_url:
        print("No publish URL — skipping social shares", file=sys.stderr)
        return

    bsky_handle = os.environ.get("BSKY_HANDLE")
    bsky_password = os.environ.get("BSKY_APP_PASSWORD")
    if bsky_handle and bsky_password:
        try:
            bluesky.post(teaser, post_url, title, teaser, bsky_handle, bsky_password)
            print("Posted to Bluesky", file=sys.stderr)
        except Exception as e:
            print(f"Bluesky post failed: {e}", file=sys.stderr)
    else:
        print("BSKY_HANDLE/BSKY_APP_PASSWORD not set — skipping Bluesky", file=sys.stderr)

    li_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    li_urn = os.environ.get("LINKEDIN_PERSON_URN")
    if li_token and li_urn:
        try:
            linkedin.post(teaser, post_url, title, li_token, li_urn)
            print("Posted to LinkedIn", file=sys.stderr)
        except Exception as e:
            print(f"LinkedIn post failed: {e}", file=sys.stderr)
    else:
        print("LINKEDIN_ACCESS_TOKEN/LINKEDIN_PERSON_URN not set — skipping LinkedIn", file=sys.stderr)

    reddit_id = os.environ.get("REDDIT_CLIENT_ID")
    reddit_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    reddit_user = os.environ.get("REDDIT_USERNAME")
    reddit_pass = os.environ.get("REDDIT_PASSWORD")
    if reddit_id and reddit_secret and reddit_user and reddit_pass:
        subreddits = REDDIT_SUBREDDITS.get(mode, REDDIT_SUBREDDITS["tech"])
        try:
            reddit.post(title, post_url, subreddits, reddit_id, reddit_secret, reddit_user, reddit_pass)
            print(f"Posted to Reddit: {subreddits}", file=sys.stderr)
        except Exception as e:
            print(f"Reddit post failed: {e}", file=sys.stderr)
    else:
        print("Reddit credentials not set — skipping Reddit", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Read items from FILE instead of stdin")
    parser.add_argument("--dry-run", action="store_true", help="Print message without posting")
    parser.add_argument("--mode", default="tech", choices=["tech", "science", "news", "finance"], help="Digest mode (default: tech)")
    parser.add_argument("--channel", help="Slack channel override")
    parser.add_argument("--telegram", action="store_true", help="Deliver via cc-connect (Telegram) instead of Slack")
    parser.add_argument("--publish", action="store_true", help="Publish to Medium and share on Bluesky, LinkedIn, Reddit")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    date_str = datetime.now(timezone.utc).strftime("%A, %B %-d")
    if args.mode == "science":
        label = "Science Digest"
        channel = args.channel or SCIENCE_CHANNEL
    elif args.mode == "news":
        label = "News Digest"
        channel = args.channel or NEWS_CHANNEL
    elif args.mode == "finance":
        label = "Finance Digest"
        channel = args.channel or FINANCE_CHANNEL
    else:
        label = "Tech Digest"
        channel = args.channel or SLACK_CHANNEL

    # New sectioned format
    if isinstance(data, dict) and "rss" in data:
        rss_items = data["rss"]
        sections = data.get("sections", {})
    else:
        rss_items = data
        sections = {}

    # Flatten all items for description generation
    section_items = [(name, item) for name, items in sections.items() for item in items]
    all_items = rss_items + [item for _, item in section_items]

    if not all_items:
        print("No items to deliver.", file=sys.stderr)
        return

    seen = load_seen_items()
    annotate_seen(all_items, seen)

    print("Generating descriptions...", file=sys.stderr)
    descriptions = generate_descriptions(all_items, args.mode)
    rss_descs = descriptions[:len(rss_items)]
    section_descs = descriptions[len(rss_items):]

    print("Fetching images...", file=sys.stderr)
    og_images = fetch_og_images(all_items)
    fetched = sum(1 for v in og_images.values() if v)
    print(f"  Got {fetched}/{len(all_items)} images", file=sys.stderr)

    formatted_rss = [format_item(item, desc) for item, desc in zip(rss_items, rss_descs)]

    # Group section messages: header per section, then one message per item
    # Each entry is (text, attachments_or_None)
    section_messages = []
    desc_idx = 0
    for name, items in sections.items():
        section_messages.append((f"*{name}*", None))
        for item in items:
            text = format_item(item, section_descs[desc_idx])
            thumb = item.get("thumbnail") or og_images.get(item["url"])
            attachments = [{"image_url": thumb, "fallback": item.get("title", "")}] if thumb else None
            section_messages.append((text, attachments))
            desc_idx += 1

    total_items = len(rss_items) + len(section_items)
    header = f"*{label} — {date_str}* ({total_items} items)"

    if args.dry_run:
        print(header)
        for msg in formatted_rss:
            print("\n---\n" + msg)
        for msg, _ in section_messages:
            print("\n---\n" + msg)
        update_seen(all_items, seen)
        save_seen_items(seen)
        return

    if args.telegram:
        tg_parts = [f"*{label} — {date_str}* ({total_items} items)"]
        for item, desc in zip(rss_items, rss_descs):
            tg_parts.append(format_item_telegram(item, desc))
        desc_idx = 0
        for name, items in sections.items():
            tg_parts.append(f"\n*{name}*")
            for item in items:
                tg_parts.append(format_item_telegram(item, section_descs[desc_idx]))
                desc_idx += 1
        post_to_telegram("\n\n".join(tg_parts))
        print(f"Posted {total_items} items via cc-connect", file=sys.stderr)
    else:
        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
            sys.exit(1)
        thread_ts = post_to_slack(header, token, channel)
        for item, msg in zip(rss_items, formatted_rss):
            img = og_images.get(item["url"])
            attachments = [{"image_url": img, "fallback": item.get("title", "")}] if img else None
            post_to_slack(msg, token, channel, thread_ts=thread_ts, unfurl=not bool(attachments), attachments=attachments)
        for msg, attachments in section_messages:
            post_to_slack(msg, token, channel, thread_ts=thread_ts, unfurl=attachments is None, attachments=attachments)
        print(f"Posted {total_items} items to #{channel}", file=sys.stderr)
    update_seen(all_items, seen)
    save_seen_items(seen)

    if args.publish:
        _publish_to_socials(label, date_str, rss_items, rss_descs, sections, section_descs, args.mode)


if __name__ == "__main__":
    main()
