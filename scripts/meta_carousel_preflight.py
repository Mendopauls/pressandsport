#!/usr/bin/env python3
"""Read-only preflight for PressSport carousel. Never calls Meta or publishes."""
import json
import sys
from pathlib import Path

MANIFEST = Path("publishing/presssport-2026-10-28.json")
ACCOUNT = "17841425937268080"
BASE = "https://pressandsport.it/instagram-media/2026-10-28/"
def main():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    urls = data.get("image_urls")
    assert data.get("instagram_account_id") == ACCOUNT, "Wrong Instagram account"
    assert isinstance(urls, list) and len(urls) == 7, "Exactly seven images required"
    expected = [BASE + f"PressSport_Carosello_Slide_{i:02d}_di_07.jpg" for i in range(1,8)]
    assert urls == expected, "Image URL order or naming mismatch"
    assert len(set(urls)) == 7, "Duplicate image URL"
    caption = data.get("caption", "")
    assert isinstance(caption, str), "Caption must be text"
    assert data.get("status") in ("draft", "approved"), "Invalid status"
    print("PASS: manifest account, 7 ordered URLs, draft/approval state")
    print("CAPTION:", "PRESENT" if caption.strip() else "MISSING")
    print("APPROVAL:", data["status"])
    print("PUBLICATION: NOT PERFORMED")
    if not caption.strip():
        print("BLOCKED: no caption; cannot proceed to publishing")
    if data["status"] != "approved":
        print("BLOCKED: manifest not approved")
    return 0
if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, ValueError, KeyError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
