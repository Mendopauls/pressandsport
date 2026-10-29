#!/usr/bin/env python3
"""Cloud integration preflight: real Supabase read-only, no Meta writes.

Fails closed unless the repository's separate publication authorization is disabled.
This is an infrastructure test, not a live publishing entry point.
"""
import json
import os
from pathlib import Path
from scripts.check_publication_authorization import validate, MANIFEST, AUTHORIZATION
from scripts.presssport_database_readonly import inspect_publication_ledger

def verify_cloud_readiness(connect, database_url, *, manifest_bytes, authorization):
    if authorization.get("publish_authorized") is not False:
        raise PermissionError("cloud preflight must not run with publishing authorized")
    blockers = validate(manifest_bytes, authorization)
    if not blockers:
        raise RuntimeError("publication authorization unexpectedly valid")
    ledger = inspect_publication_ledger(connect, database_url)
    return {"database": ledger, "authorization_blocked": True,
            "meta_write_attempted": False, "publication_performed": False}

def main():
    import psycopg
    manifest = MANIFEST.read_bytes()
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    result = verify_cloud_readiness(psycopg.connect,
                                    os.environ.get("PRESSSPORT_DATABASE_URL"),
                                    manifest_bytes=manifest,
                                    authorization=auth)
    print("PASS: cloud preflight; private ledger read-only")
    print("Reservation count:", result["database"]["reservation_count"])
    print("PASS: separate publication authorization remains disabled")
    print("PUBLICATION: NOT PERFORMED")

if __name__ == "__main__":
    main()
