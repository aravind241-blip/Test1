"""
Posts an image + caption to Instagram (Business/Creator account) and a
Facebook Page, using the Graph API. Both require the image to be reachable
at a public URL (we pass the GitHub Pages URL for the generated image).
"""

import os
import time
import requests

GRAPH_VERSION = "v20.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

IG_USER_ID = os.environ.get("IG_USER_ID", "").strip()
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "").strip()
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()


def post_to_instagram(image_url: str, caption: str) -> dict:
    if not (IG_USER_ID and IG_ACCESS_TOKEN):
        print("[instagram] missing IG_USER_ID / IG_ACCESS_TOKEN, skipping")
        return {"skipped": True}

    # Step 1: create media container
    create_resp = requests.post(
        f"{GRAPH_BASE}/{IG_USER_ID}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    create_resp.raise_for_status()
    creation_id = create_resp.json()["id"]

    # Step 2: publish the container (poll briefly in case IG is still processing)
    for attempt in range(5):
        publish_resp = requests.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media_publish",
            data={"creation_id": creation_id, "access_token": IG_ACCESS_TOKEN},
            timeout=30,
        )
        if publish_resp.status_code == 200:
            return publish_resp.json()
        time.sleep(5)

    publish_resp.raise_for_status()
    return publish_resp.json()


def post_to_facebook(image_url: str, caption: str) -> dict:
    if not (FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN):
        print("[facebook] missing FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN, skipping")
        return {"skipped": True}

    resp = requests.post(
        f"{GRAPH_BASE}/{FB_PAGE_ID}/photos",
        data={
            "url": image_url,
            "caption": caption,
            "access_token": FB_PAGE_ACCESS_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
