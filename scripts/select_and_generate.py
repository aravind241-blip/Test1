"""
Phase 1 (runs first, before the GitHub Pages image is public):
  1. Fetch latest news across all categories
  2. Filter out already-posted articles (state/posted_log.json)
  3. Round-robin across categories so we don't post 10 sports stories in a row
  4. Generate the image into docs/images/<uid>.png
  5. Generate the caption
  6. Write state/pending_post.json describing what still needs to be published

This script only touches local files - it does NOT call any social API and
does NOT need network access to Facebook/Instagram. Git commit/push happens
in the GitHub Actions workflow, between this script and publish_post.py.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from fetch_news import fetch_all
from generate_image import generate as generate_image
from generate_caption import generate as generate_caption

ROOT = os.path.join(os.path.dirname(__file__), "..")
STATE_DIR = os.path.join(ROOT, "state")
DOCS_IMAGES_DIR = os.path.join(ROOT, "docs", "images")
POSTED_LOG_PATH = os.path.join(STATE_DIR, "posted_log.json")
ROTATION_PATH = os.path.join(STATE_DIR, "rotation.json")
PENDING_PATH = os.path.join(STATE_DIR, "pending_post.json")

CATEGORY_ORDER = ["india", "world", "business", "sports"]

MAX_LOG_SIZE = 1000


def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    os.makedirs(STATE_DIR, exist_ok=True)
    os.makedirs(DOCS_IMAGES_DIR, exist_ok=True)

    posted_log = _load_json(POSTED_LOG_PATH, {"uids": []})
    posted_uids = set(posted_log.get("uids", []))

    rotation = _load_json(ROTATION_PATH, {"last_category": None})
    last_category = rotation.get("last_category")

    print("Fetching news...")
    articles = fetch_all()
    print(f"Fetched {len(articles)} unique articles total")

    unposted = [a for a in articles if a["uid"] not in posted_uids]
    print(f"{len(unposted)} unposted articles available")

    if not unposted:
        print("Nothing new to post. Exiting.")
        _save_json(PENDING_PATH, {})
        return

    by_category = {}
    for a in unposted:
        by_category.setdefault(a["category"], []).append(a)

    # round-robin: try the category *after* the last one posted
    ordered_categories = CATEGORY_ORDER[:]
    if last_category in ordered_categories:
        idx = ordered_categories.index(last_category)
        ordered_categories = ordered_categories[idx + 1 :] + ordered_categories[: idx + 1]

    chosen = None
    for cat in ordered_categories:
        if by_category.get(cat):
            chosen = by_category[cat][0]
            break
    if chosen is None:
        chosen = unposted[0]

    print(f"Selected article: [{chosen['category']}] {chosen['title']}")

    image_filename = f"{chosen['uid']}.png"
    image_path = os.path.join(DOCS_IMAGES_DIR, image_filename)
    generate_image(chosen, image_path)
    print(f"Image saved to {image_path}")

    caption = generate_caption(chosen)

    pending = {
        "uid": chosen["uid"],
        "title": chosen["title"],
        "category": chosen["category"],
        "source": chosen["source"],
        "url": chosen["url"],
        "image_rel_path": f"images/{image_filename}",
        "caption": caption,
    }
    _save_json(PENDING_PATH, pending)
    print("Wrote pending_post.json")

    rotation["last_category"] = chosen["category"]
    _save_json(ROTATION_PATH, rotation)


if __name__ == "__main__":
    main()
