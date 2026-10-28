#!/usr/bin/env python3
"""Read-only duplicate publication guard; no Meta calls or file writes."""
import argparse
import json
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="publishing/presssport-2026-10-28.json")
    parser.add_argument("--ledger", default="publishing/publication-ledger.json")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    if not isinstance(ledger, list):
        raise ValueError("ledger must be a list")
    account = manifest["instagram_account_id"]
    urls = manifest["image_urls"]
    if not isinstance(urls, list) or not urls:
        raise ValueError("manifest has no media")
    matches = [
        item for item in ledger
        if isinstance(item, dict)
        and item.get("instagram_account_id") == account
        and item.get("image_urls") == urls
        and item.get("status") in ("publishing", "published", "uncertain")
    ]
    if matches:
        print("BLOCKED: same account and media already publishing, published, or uncertain")
        return 1
    print("PASS: no matching entry in versioned publication ledger")
    print("NOTE: read-only check; not an atomic lock and not sufficient alone to prevent duplicates")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("BLOCKED: ledger or manifest invalid:", type(exc).__name__)
        sys.exit(1)
