#!/usr/bin/env python3
"""Read-only release authorization gate. Never calls Meta or publishes."""
import json
import sys
from pathlib import Path

MANIFEST = Path("publishing/presssport-2026-10-28.json")
AUTHORIZATION = Path("publishing/presssport-2026-10-28-authorization.json")

def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    failures = []
    if manifest.get("status") != "approved":
        failures.append("editorial approval missing")
    if auth.get("instagram_account_id") != manifest.get("instagram_account_id"):
        failures.append("account mismatch")
    if auth.get("manifest_path") != MANIFEST.as_posix():
        failures.append("manifest mismatch")
    if auth.get("publish_authorized") is not True:
        failures.append("separate publication authorization not granted")
    if auth.get("approved_by") != "Paolo Savio":
        failures.append("named publisher approval missing")
    if not isinstance(auth.get("authorized_at"), str) or not auth["authorized_at"].strip():
        failures.append("authorization timestamp missing")
    if auth.get("action") not in ("publish_now", "schedule"):
        failures.append("publication action not selected")
    if auth.get("action") == "schedule" and not auth.get("scheduled_at"):
        failures.append("schedule time missing")
    if failures:
        for reason in failures:
            print("BLOCKED:", reason)
        print("PUBLICATION: NOT PERFORMED")
        return 1
    print("PASS: separate authorization record present")
    print("PUBLICATION: NOT PERFORMED")
    print("NOTE: future publisher must also verify authorization is current and bind it to an immutable manifest revision.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("BLOCKED: invalid authorization:", type(exc).__name__)
        sys.exit(1)
