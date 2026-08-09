"""
Generates an Instagram/Facebook caption + hashtags for an article, based on
its title/description/category. Pure rule-based (no external API needed),
so it works even without an LLM key.
"""

import re

CATEGORY_EMOJI = {
    "india": "🇮🇳",
    "world": "🌍",
    "business": "💼",
    "sports": "🏆",
}

CATEGORY_BASE_TAGS = {
    "india": ["#IndiaNews", "#India", "#IndianNews"],
    "world": ["#WorldNews", "#GlobalNews", "#International"],
    "business": ["#BusinessNews", "#Markets", "#Economy"],
    "sports": ["#SportsNews", "#Sports"],
}

GENERIC_TAGS = ["#BreakingNews", "#News", "#Update", "#Trending", "#NewsToday"]

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
    "with", "as", "by", "is", "are", "was", "were", "be", "has", "have",
    "had", "it", "its", "this", "that", "after", "over", "amid", "amidst",
    "into", "from", "than", "his", "her", "their", "up", "out", "new",
}


def _extract_keyword_tags(title: str, limit: int = 4) -> list:
    """Pull capitalized/proper-noun-ish words from the title to use as hashtags."""
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", title)
    seen = set()
    tags = []
    for w in words:
        wl = w.lower()
        if wl in STOPWORDS or len(w) < 3:
            continue
        if not w[0].isupper():
            continue
        tag = "#" + re.sub(r"[^A-Za-z0-9]", "", w)
        if tag.lower() not in seen and len(tag) > 2:
            seen.add(tag.lower())
            tags.append(tag)
        if len(tags) >= limit:
            break
    return tags


BRAND_NAME = "AravindNews24"


def generate(article: dict) -> str:
    category = article.get("category", "world")
    title = article.get("title", "").strip()
    description = article.get("description", "").strip()

    emoji = CATEGORY_EMOJI.get(category, "📰")

    # Trim description to a short teaser line (avoid reproducing full article text)
    teaser = ""
    if description:
        first_sentence = re.split(r"(?<=[.!?])\s+", description)[0]
        if len(first_sentence) > 140:
            first_sentence = first_sentence[:137].rsplit(" ", 1)[0] + "..."
        teaser = first_sentence

    lines = [f"{emoji} BREAKING: {title}"]
    if teaser and teaser.lower() not in title.lower():
        lines.append("")
        lines.append(teaser)
    lines.append("")
    lines.append(f"Follow {BRAND_NAME} for real-time news updates 🔔")

    hashtags = []
    hashtags.extend(CATEGORY_BASE_TAGS.get(category, []))
    hashtags.extend(_extract_keyword_tags(title))
    hashtags.extend(GENERIC_TAGS)

    # de-dup while preserving order, cap at 15 tags
    seen = set()
    final_tags = []
    for t in hashtags:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            final_tags.append(t)
        if len(final_tags) >= 15:
            break

    lines.append("")
    lines.append(" ".join(final_tags))

    return "\n".join(lines)


if __name__ == "__main__":
    sample = {
        "title": "Reserve Bank of India Cuts Interest Rates Amid Global Slowdown",
        "description": "The RBI announced a surprise rate cut today as it looks to boost economic growth amid slowing global demand.",
        "category": "business",
    }
    print(generate(sample))
