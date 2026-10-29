"""Generate a reproducible, read-only operator verification packet.

This is NOT a production release certification and cannot publish.
"""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from scripts.presssport_cloud_executor_staging import run as staging
from scripts.presssport_preproduction_audit import inspect_preproduction
from scripts.presssport_staging_boundary_check import verify_boundary

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"publishing/presssport-2026-10-28.json"
AUTH=ROOT/"publishing/presssport-2026-10-28-authorization.json"

def build_packet():
    raw=MANIFEST.read_bytes()
    manifest=json.loads(raw)
    auth=json.loads(AUTH.read_text(encoding="utf-8"))
    stage=staging()
    audit=inspect_preproduction()
    boundary=verify_boundary()
    if auth.get("publish_authorized") is not False or not audit["passed"] or not boundary["authorization_blocked"]:
        raise RuntimeError("verification packet blocked: security gates not satisfied")
    if stage["account_id"]!=manifest["instagram_account_id"] or stage["image_count"]!=len(manifest["image_urls"]):
        raise RuntimeError("verification packet blocked: inconsistent manifest")
    return {
        "packet_version":1,
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "project":"Press & Sport Cloud",
        "instagram_account_id":manifest["instagram_account_id"],
        "manifest_path":"publishing/presssport-2026-10-28.json",
        "manifest_sha256":hashlib.sha256(raw).hexdigest(),
        "image_count":len(manifest["image_urls"]),
        "caption":manifest["caption"],
        "image_urls":manifest["image_urls"],
        "offline_security_checks":audit["checks"],
        "executor_boundary":boundary,
        "staging":stage,
        "publication_authorized":False,
        "live_release_certified":False,
        "live_publication_performed":False,
        "operator_verification_required":[
            "Review exact caption and all seven images",
            "Confirm correct Instagram account and content ownership",
            "Review real cloud connectivity, Meta permissions and database state",
            "Authorize real publication separately, only after verification"
        ],
    }

def main():
    print(json.dumps(build_packet(),ensure_ascii=False,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
