#!/usr/bin/env python3
"""Cloud publisher integration DRY RUN ONLY.

This entrypoint intentionally cannot publish: no Meta POST adapter, no database
write connection, no call to execute_once. A future live entrypoint must be
separately designed, audited and explicitly authorized.
"""
import json
import os
from pathlib import Path

from scripts.check_publication_authorization import validate
from scripts.meta_identity_readonly import verify_identity
from scripts.presssport_database_readonly import inspect_publication_ledger
from scripts.presssport_ledger_reconciliation_readonly import inspect_ledger
from scripts.presssport_recovery_triage import recovery_report

MANIFEST = Path("publishing/presssport-2026-10-28.json")
AUTHORIZATION = Path("publishing/presssport-2026-10-28-authorization.json")

def run_dry_run(connect, database_url, *, manifest_bytes, authorization,
                token, verify=verify_identity):
    if authorization.get("publish_authorized") is not False:
        raise PermissionError("dry run requires publication authorization disabled")
    blockers = validate(manifest_bytes, authorization)
    if not blockers:
        raise RuntimeError("publication gate unexpectedly open")
    manifest = json.loads(manifest_bytes)
    if manifest.get("status") != "approved" or not manifest.get("image_urls"):
        raise ValueError("manifest not ready for preflight")
    identity = verify(manifest_bytes, token)
    if identity.get("verified") is not True or identity.get("account_id") != manifest.get("instagram_account_id"):
        raise RuntimeError("Meta identity not verified")
    ledger = inspect_publication_ledger(connect, database_url)
    diagnostic = inspect_ledger(connect, database_url)
    triage = recovery_report(diagnostic["review"])
    return {
        "mode": "dry_run",
        "identity_verified": True,
        "database_accessible": ledger["ledger_accessible"],
        "reservation_count": ledger["reservation_count"],
        "review_count": len(triage),
        "publication_authorized": False,
        "database_writes": False,
        "meta_post_calls": 0,
        "published": False,
    }

def main():
    import psycopg
    result = run_dry_run(
        psycopg.connect, os.environ.get("PRESSSPORT_DATABASE_URL"),
        manifest_bytes=MANIFEST.read_bytes(),
        authorization=json.loads(AUTHORIZATION.read_text(encoding="utf-8")),
        token=os.environ.get("META_INSTAGRAM_ACCESS_TOKEN", ""))
    print(json.dumps(result, indent=2, sort_keys=True))
    print("PASS: integrated cloud dry run; NO PUBLICATION")

if __name__ == "__main__":
    main()
