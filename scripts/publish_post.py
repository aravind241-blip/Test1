"""
Phase 2 (runs after the generated image has been committed, pushed, and
confirmed reachable on GitHub Pages):
  1. Read state/pending_post.json
  2. Build the public image URL from PAGES_BASE_URL
  3. Post to Instagram + Facebook
  4. Append the uid to state/posted_log.json (capped) and clear pending_post.json
"""

import os
import sys
import json
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))

from post_social import post_to_instagram, post_to_facebook

ROOT = os.path.join(os.path.dirname(__file__), "..")
STATE_DIR = os.path.join(ROOT, "state")
POSTED_LOG_PATH = os.path.join(STATE_DIR, "posted_log.json")
PENDING_PATH = os.path.join(STATE_DIR, "pending_post.json")

MAX_LOG_SIZE = 1000
PAGES_BASE_URL = os.environ.get("PAGES_BASE_URL", "").strip().rstrip("/")


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


def _wait_until_live(url: str, timeout_seconds: int = 120, interval: int = 5) -> bool:
    """Poll the public URL until it returns 200 (GitHub Pages deploy lag)."""
    elapsed = 0
    while elapsed < timeout_seconds:
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(interval)
        elapsed += interval
    return False


def main():
    pending = _load_json(PENDING_PATH, {})
    if not pending:
        print("No pending post. Exiting.")
        return

    if not PAGES_BASE_URL:
        print("ERROR: PAGES_BASE_URL is not set (e.g. https://username.github.io/reponame)")
        sys.exit(1)

    image_url = f"{PAGES_BASE_URL}/{pending['image_rel_path']}"
    print(f"Waiting for image to go live at: {image_url}")

    if not _wait_until_live(image_url):
        print("ERROR: image never became publicly reachable in time. Aborting this cycle.")
        sys.exit(1)

    caption = pending["caption"]

    print("Posting to Instagram...")
    try:
        ig_result = post_to_instagram(image_url, caption)
        print(f"Instagram result: {ig_result}")
    except Exception as e:
        print(f"Instagram post FAILED: {e}")

    print("Posting to Facebook...")
    try:
        fb_result = post_to_facebook(image_url, caption)
        print(f"Facebook result: {fb_result}")
    except Exception as e:
        print(f"Facebook post FAILED: {e}")

    # mark as posted regardless of individual platform failures, so we don't
    # get stuck retrying the same story forever
    posted_log = _load_json(POSTED_LOG_PATH, {"uids": []})
    uids = posted_log.get("uids", [])
    uids.append(pending["uid"])
    uids = uids[-MAX_LOG_SIZE:]
    posted_log["uids"] = uids
    _save_json(POSTED_LOG_PATH, posted_log)

    _save_json(PENDING_PATH, {})
    print("Done. Logged uid and cleared pending_post.json")


if __name__ == "__main__":
    main()
