#!/usr/bin/env python3
"""Read-only publication authorization gate, bound to exact manifest bytes."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = Path("publishing/presssport-2026-10-28.json")
AUTHORIZATION = Path("publishing/presssport-2026-10-28-authorization.json")

def validate(manifest_bytes, auth, now=None):
    manifest = json.loads(manifest_bytes)
    problems = []
    if manifest.get("status") != "approved":
        problems.append("editorial approval missing")
    if auth.get("instagram_account_id") != manifest.get("instagram_account_id"):
        problems.append("account mismatch")
    if auth.get("manifest_path") != MANIFEST.as_posix():
        problems.append("manifest mismatch")
    if auth.get("publish_authorized") is not True:
        problems.append("separate publication authorization not granted")
    if auth.get("approved_by") != "Paolo Savio":
        problems.append("named publisher approval missing")
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    if auth.get("manifest_sha256") != digest:
        problems.append("manifest digest missing or does not match approved content")
    action = auth.get("action")
    if action not in ("publish_now", "schedule"):
        problems.append("publication action not selected")
    timestamp = auth.get("authorized_at")
    try:
        if not isinstance(timestamp, str):
            raise ValueError("missing timestamp")
        approved_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if approved_at.tzinfo is None:
            raise ValueError("timezone required")
        now = now or datetime.now(timezone.utc)
        age = (now - approved_at).total_seconds()
        if age < -300 or age > 3600:
            problems.append("authorization outside one-hour validity window")
    except ValueError:
        problems.append("invalid authorization timestamp")
    if action == "schedule":
        try:
            scheduled = datetime.fromisoformat(str(auth.get("scheduled_at")).replace("Z", "+00:00"))
            if scheduled.tzinfo is None or scheduled <= (now or datetime.now(timezone.utc)):
                raise ValueError("schedule must be future and timezone-aware")
        except ValueError:
            problems.append("invalid scheduled publication time")
    return problems

def main():
    manifest_bytes = MANIFEST.read_bytes()
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    problems = validate(manifest_bytes, auth)
    for reason in problems:
        print("BLOCKED:", reason)
    print("PUBLICATION: NOT PERFORMED")
    if problems:
        return 1
    print("PASS: separate authorization matches immutable manifest and is recent")
    print("NOTE: no identity verification or atomic lock; publisher requires additional safeguards")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("BLOCKED: invalid authorization:", type(exc).__name__)
        sys.exit(1)
