#!/usr/bin/env python3
"""Meta Graph carousel request contracts; no HTTP or database side effects.

Transport and token injection belong to the separately authorized publisher.
"""
from scripts.meta_carousel_plan import plan_carousel

def child_requests(manifest_bytes):
    plan = plan_carousel(manifest_bytes)
    account = plan["instagram_account_id"]
    return [{"method": "POST", "path": f"/{account}/media",
             "form": dict(child)} for child in plan["children"]]

def parent_request(manifest_bytes, child_ids):
    plan = plan_carousel(manifest_bytes)
    if not isinstance(child_ids, list) or len(child_ids) != len(plan["children"]):
        raise ValueError("one ready child ID required per image")
    if any(not isinstance(x, str) or not x.isdecimal() for x in child_ids):
        raise ValueError("invalid child container ID")
    if len(set(child_ids)) != len(child_ids):
        raise ValueError("duplicate child container ID")
    form = dict(plan["parent"])
    form["children"] = ",".join(child_ids)
    return {"method": "POST", "path": f"/{plan['instagram_account_id']}/media",
            "form": form}

def publish_request(manifest_bytes, parent_id):
    plan = plan_carousel(manifest_bytes)
    if not isinstance(parent_id, str) or not parent_id.isdecimal():
        raise ValueError("invalid parent container ID")
    return {"method": "POST",
            "path": f"/{plan['instagram_account_id']}/media_publish",
            "form": {"creation_id": parent_id}}
