#!/usr/bin/env python3
"""Read-only Meta Graph API identity check; never creates or publishes media."""
import json
import os
import sys
import urllib.parse
import urllib.request

ACCOUNT = "17841425937268080"
VERSION = "v26.0"

def main():
    token = os.getenv("META_INSTAGRAM_ACCESS_TOKEN", "")
    if not token:
        print("BLOCKED: META_INSTAGRAM_ACCESS_TOKEN is not configured in GitHub secrets.")
        return 2
    query = urllib.parse.urlencode({"fields": "id,username", "access_token": token})
    request = urllib.request.Request(
        f"https://graph.facebook.com/{VERSION}/{ACCOUNT}?{query}",
        headers={"User-Agent": "PressSport-Cloud-ReadOnly/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
    except Exception as exc:
        print("FAIL: Meta identity request failed (credentials, permissions or network).")
        return 1
    if str(data.get("id")) != ACCOUNT or data.get("username", "").lower() != "pressandsport":
        print("FAIL: account identity mismatch.")
        return 1
    print("PASS: Meta account verified: @pressandsport.")
    print("READ ONLY: no creation or publication attempted.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
