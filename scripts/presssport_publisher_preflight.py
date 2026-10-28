#!/usr/bin/env python3
"""Offline publication coordinator for safe preflight; no Meta or database writes.

Production publishing is deliberately not wired. This module validates the exact
manifest, authorization, account identity assertion and carousel request plan.
"""
from scripts.check_publication_authorization import validate
from scripts.meta_carousel_requests import child_requests
from scripts.meta_publisher_execution_plan import build_execution_plan

def preflight(manifest_bytes, authorization, *, identity_verified=False, now=None):
    blockers = validate(manifest_bytes, authorization, now=now)
    if not identity_verified:
        blockers.append("Meta account identity not independently verified")
    if blockers:
        return {"ready": False, "blockers": blockers, "publication_performed": False}
    plan = build_execution_plan(manifest_bytes, authorization,
                                identity_verified=True, now=now)
    requests = child_requests(manifest_bytes)
    return {"ready": True, "account_id": plan["instagram_account_id"],
            "image_count": len(requests), "steps": plan["steps"],
            "publication_performed": False}
