"""
Fetches breaking news from GNews API (primary) and RSS feeds (secondary/fallback)
across categories: india, world, business, sports.

Returns a de-duplicated, normalized list of article dicts:
    {
        "title": str,
        "description": str,
        "url": str,
        "source": str,
        "category": "india" | "world" | "business" | "sports",
        "published_at": str (ISO8601),
        "uid": str  (stable hash used for de-dup / posted-log)
    }
"""

import os
import re
import hashlib
import datetime
import requests
import feedparser

GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY", "").strip()

# ---- GNews category mapping -------------------------------------------------
GNEWS_CATEGORIES = {
    "india": {"category": "nation", "country": "in"},
    "world": {"category": "world", "country": None},
    "business": {"category": "business", "country": None},
    "sports": {"category": "sports", "country": None},
}

# ---- RSS fallback / supplementary feeds -------------------------------------
RSS_FEEDS = {
    "india": [
        "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",  # TOI India
        "https://www.thehindu.com/news/national/feeder/default.rss",
    ],
    "world": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.dw.com/rdf/rss-en-world",
    ],
    "business": [
        "https://www.moneycontrol.com/rss/business.xml",
        "http://feeds.bbci.co.uk/news/business/rss.xml",
    ],
    "sports": [
        "https://www.espn.com/espn/rss/news",
        "http://feeds.bbci.co.uk/sport/rss.xml",
    ],
}


def _make_uid(title: str, url: str) -> str:
    raw = (title.strip().lower() + "|" + url.strip().lower()).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _from_gnews(category: str) -> list:
    if not GNEWS_API_KEY:
        return []
    conf = GNEWS_CATEGORIES[category]
    params = {
        "category": conf["category"],
        "lang": "en",
        "max": 10,
        "apikey": GNEWS_API_KEY,
    }
    if conf["country"]:
        params["country"] = conf["country"]

    try:
        resp = requests.get(
            "https://gnews.io/api/v4/top-headlines", params=params, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[gnews] fetch failed for {category}: {e}")
        return []

    articles = []
    for a in data.get("articles", []):
        title = (a.get("title") or "").strip()
        url = a.get("url") or ""
        if not title or not url:
            continue
        articles.append(
            {
                "title": title,
                "description": (a.get("description") or "").strip(),
                "url": url,
                "source": (a.get("source") or {}).get("name", "News"),
                "category": category,
                "published_at": a.get("publishedAt")
                or datetime.datetime.utcnow().isoformat(),
                "image_url": (a.get("image") or "").strip() or None,
                "uid": _make_uid(title, url),
            }
        )
    return articles


def _extract_rss_image(entry) -> str:
    """Best-effort extraction of an article thumbnail from an RSS/Atom entry."""
    # media:thumbnail / media:content (feedparser exposes these directly)
    media_thumb = entry.get("media_thumbnail")
    if media_thumb:
        url = media_thumb[0].get("url")
        if url:
            return url

    media_content = entry.get("media_content")
    if media_content:
        url = media_content[0].get("url")
        if url:
            return url

    # <enclosure> tags
    for enc in entry.get("enclosures", []) or []:
        if str(enc.get("type", "")).startswith("image") or enc.get("href", "").lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp")
        ):
            return enc.get("href")

    # Sometimes an <img> is embedded in the summary/content HTML
    html_blob = entry.get("summary", "") or ""
    match = re.search(r'<img[^>]+src="([^"]+)"', html_blob)
    if match:
        return match.group(1)

    return None


def _from_rss(category: str) -> list:
    articles = []
    for feed_url in RSS_FEEDS.get(category, []):
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"[rss] fetch failed for {feed_url}: {e}")
            continue

        source_name = feed.feed.get("title", "News") if hasattr(feed, "feed") else "News"

        for entry in feed.entries[:10]:
            title = (entry.get("title") or "").strip()
            url = entry.get("link") or ""
            if not title or not url:
                continue
            description = (entry.get("summary") or entry.get("description") or "").strip()
            description = re.sub(r"<[^>]+>", "", description).strip()  # strip HTML tags
            published = entry.get("published", "") or datetime.datetime.utcnow().isoformat()
            articles.append(
                {
                    "title": title,
                    "description": description,
                    "url": url,
                    "source": source_name,
                    "category": category,
                    "published_at": published,
                    "image_url": _extract_rss_image(entry),
                    "uid": _make_uid(title, url),
                }
            )
    return articles


def fetch_all() -> list:
    """Fetch and merge news from all sources across all categories."""
    all_articles = []
    seen_uids = set()

    for category in GNEWS_CATEGORIES:
        combined = _from_gnews(category) + _from_rss(category)
        for art in combined:
            if art["uid"] not in seen_uids:
                seen_uids.add(art["uid"])
                all_articles.append(art)

    return all_articles


if __name__ == "__main__":
    results = fetch_all()
    print(f"Fetched {len(results)} unique articles")
    for r in results[:5]:
        print(f"  [{r['category']}] {r['title']} ({r['source']})")
