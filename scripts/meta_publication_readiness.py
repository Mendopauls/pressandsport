#!/usr/bin/env python3
"""Fail-closed publication readiness gate. Read-only; never calls Meta."""
import json
import sys
from pathlib import Path

MANIFEST = Path("publishing/presssport-2026-10-28.json")
EXPECTED_ACCOUNT = "17841425937268080"
EXPECTED_BASE = "https://pressandsport.it/instagram-media/2026-10-28/"
EXPECTED_URLS = [EXPECTED_BASE + f"PressSport_Carosello_Slide_{n:02d}_di_07.jpg" for n in range(1, 8)]

def check(data):
    failures = []
    if data.get("instagram_account_id") != EXPECTED_ACCOUNT:
        failures.append("wrong Instagram account")
    if data.get("image_urls") != EXPECTED_URLS:
        failures.append("image list must contain the seven approved JPEGs in order")
    if data.get("status") != "approved":
        failures.append("manifest status is not approved")
    caption = data.get("caption")
    if not isinstance(caption, str) or not caption.strip():
        failures.append("approved caption is missing")
    if isinstance(caption, str) and len(caption) > 2200:
        failures.append("caption exceeds 2200 characters")
    return failures

def main():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = check(data)
    if failures:
        for failure in failures:
            print("BLOCKED:", failure)
        print("PUBLICATION: NOT PERFORMED")
        return 1
    print("READY: manifest and caption approved")
    print("PUBLICATION: NOT PERFORMED")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError) as exc:
        print("BLOCKED: invalid or unreadable manifest:", type(exc).__name__)
        sys.exit(1)
