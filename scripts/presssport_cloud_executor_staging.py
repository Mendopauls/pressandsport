#!/usr/bin/env python3
"""Cloud executor staging check: no publishing, no database writes."""
import json
from pathlib import Path
from scripts.presssport_execution_readiness import assess
from scripts.presssport_preproduction_audit import inspect_preproduction
from scripts.presssport_staging_boundary_check import verify_boundary

MANIFEST=Path("publishing/presssport-2026-10-28.json")
AUTH=Path("publishing/presssport-2026-10-28-authorization.json")

def run():
    readiness=assess(MANIFEST.read_bytes(),json.loads(AUTH.read_text(encoding="utf-8")))
    safety=inspect_preproduction()
    boundary=verify_boundary()
    if not safety["passed"] or not readiness["authorization_blockers"] or not boundary["authorization_blocked"]:
        raise RuntimeError("staging safety gate failed")
    return {"mode":"staging_only","account_id":readiness["account_id"],
            "image_count":readiness["image_count"],
            "security_audit_passed":True,
            "executor_boundary_blocked":True,
            "external_calls":boundary["external_calls"],
            "live_execution_enabled":False,
            "published":False}

def main():
    print(json.dumps(run(),indent=2,sort_keys=True))
    print("PASS: staging only; no publication")

if __name__=="__main__":
    main()
