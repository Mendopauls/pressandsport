#!/usr/bin/env python3
"""Side-effect-free execution plan for the future Meta carousel publisher.

No database connections, token access, or Meta API calls are performed.
"""
from scripts.meta_carousel_plan import plan_carousel
from scripts.check_publication_authorization import validate

def build_execution_plan(manifest_bytes, authorization, *, identity_verified=False, now=None):
    blockers = validate(manifest_bytes, authorization, now=now)
    if not identity_verified:
        blockers.append("Meta account identity not independently verified")
    if blockers:
        raise PermissionError("; ".join(blockers))
    payload = plan_carousel(manifest_bytes)
    steps = [
        "reserve_unique_publication_key",
        "commit_reservation",
        "transition_reserved_to_publishing",
        "commit_publishing_state",
    ]
    steps += ["create_carousel_child_container"] * len(payload["children"])
    steps += [
        "wait_for_child_container_readiness",
        "create_carousel_parent_container",
        "wait_for_parent_container_readiness",
        "publish_parent_once",
        "record_published_or_uncertain",
    ]
    return {"instagram_account_id": payload["instagram_account_id"],
            "image_count": len(payload["children"]),
            "steps": steps,
            "mode": "PLAN_ONLY_NO_SIDE_EFFECTS"}
