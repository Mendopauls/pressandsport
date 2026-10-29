"""Offline readiness checks. No external side effects."""
import json
from scripts.check_publication_authorization import validate

def assess(manifest_bytes, authorization, now=None):
    manifest=json.loads(manifest_bytes)
    return {"account_id":manifest.get("instagram_account_id"),
            "image_count":len(manifest.get("image_urls",[])),
            "authorization_blockers":validate(manifest_bytes,authorization,now=now),
            "live_execution_enabled":False}
