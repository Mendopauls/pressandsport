#!/usr/bin/env python3
"""Read-only verification of the Instagram account bound to an approved manifest.

Uses GET only; never creates containers, publishes, or writes to a database.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def verify_identity(manifest_bytes, token, *, opener=urlopen):
    manifest = json.loads(manifest_bytes)
    account = manifest.get("instagram_account_id")
    if not isinstance(account, str) or not account.isdecimal():
        raise ValueError("invalid Instagram account ID")
    if not isinstance(token, str) or not token:
        raise ValueError("missing Meta access token")
    url = "https://graph.facebook.com/v24.0/" + account + "?" + urlencode({
        "fields": "id,username", "access_token": token})
    with opener(Request(url, method="GET"), timeout=15) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict) or payload.get("id") != account:
        raise RuntimeError("Meta identity mismatch")
    username = payload.get("username")
    if username != "pressandsport":
        raise RuntimeError("Meta username mismatch")
    return {"verified": True, "account_id": account, "username": username}

def main():
    manifest = Path("publishing/presssport-2026-10-28.json").read_bytes()
    result = verify_identity(manifest, os.environ.get("META_INSTAGRAM_ACCESS_TOKEN", ""))
    print("PASS: verified Meta account", result["username"])
    print("PUBLICATION: NOT PERFORMED")

if __name__ == "__main__":
    main()
