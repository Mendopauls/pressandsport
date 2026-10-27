#!/usr/bin/env python3
"""Publish an explicitly approved carousel via the official Instagram Graph API.

Never publishes without APPROVED=true and a matching approved manifest.
Credentials are supplied as GitHub Actions secrets, not committed to the repo.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MANIFEST = Path("publishing/presssport-2026-10-28.json")
API_VERSION = os.environ.get("META_GRAPH_VERSION", "v24.0")
BASE = f"https://graph.facebook.com/{API_VERSION}"
ACCOUNT = "17841425937268080"

def graph_post(endpoint, params, token):
    payload = urllib.parse.urlencode({**params, "access_token": token}).encode()
    req = urllib.request.Request(f"{BASE}/{endpoint}", data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Meta API HTTP {exc.code}: {exc.read().decode()[:1200]}") from exc

def graph_get(endpoint, params, token):
    query = urllib.parse.urlencode({**params, "access_token": token})
    req = urllib.request.Request(f"{BASE}/{endpoint}?{query}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)

def main():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    urls = data["image_urls"]
    if data["instagram_account_id"] != ACCOUNT or len(urls) != 7:
        raise SystemExit("Unexpected account or image count")
    if not all(url.startswith("https://pressandsport.it/instagram-media/2026-10-28/") and url.endswith(".jpg") for url in urls):
        raise SystemExit("Unexpected image URL")
    if data.get("status") != "approved" or os.environ.get("APPROVED") != "true":
        raise SystemExit("Not approved: publication blocked")
    token = os.environ.get("META_INSTAGRAM_ACCESS_TOKEN")
    if not token:
        raise SystemExit("Missing META_INSTAGRAM_ACCESS_TOKEN secret")
    children = []
    for index, url in enumerate(urls, 1):
        child = graph_post(f"{ACCOUNT}/media", {"image_url": url, "is_carousel_item": "true"}, token)
        child_id = child["id"]
        children.append(child_id)
        print(f"Created child container {index}/7")
    parent = graph_post(f"{ACCOUNT}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": data["caption"],
    }, token)
    parent_id = parent["id"]
    for attempt in range(24):
        status = graph_get(parent_id, {"fields": "status_code,status"}, token)
        code = status.get("status_code")
        print(f"Carousel processing: {code}")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container failed: {status}")
        time.sleep(10)
    else:
        raise RuntimeError("Timed out waiting for carousel processing")
    published = graph_post(f"{ACCOUNT}/media_publish", {"creation_id": parent_id}, token)
    print("Published media ID:", published["id"])

if __name__ == "__main__":
    main()
