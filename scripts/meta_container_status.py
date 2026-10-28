#!/usr/bin/env python3
"""Pure Meta container-status validation and readiness decisions.

No HTTP, sleeps, token handling or automatic retry. The caller must retrieve
the status from Meta and apply an explicit, bounded polling policy.
"""
VALID_STATUSES = frozenset({"IN_PROGRESS", "FINISHED", "ERROR", "EXPIRED", "PUBLISHED"})

class ContainerStatusError(ValueError):
    pass

def validate_container_id(container_id):
    if not isinstance(container_id, str) or not container_id.isdecimal():
        raise ContainerStatusError("invalid Meta container ID")
    return container_id

def status_request(container_id):
    validate_container_id(container_id)
    return {"method": "GET", "path": f"/{container_id}", "params": {"fields": "id,status_code"}}

def classify_container_status(container_id, response):
    validate_container_id(container_id)
    if not isinstance(response, dict) or response.get("id") != container_id:
        raise ContainerStatusError("Meta status response does not match container ID")
    status = response.get("status_code")
    if status not in VALID_STATUSES:
        raise ContainerStatusError("unknown or missing Meta status; fail closed")
    if status == "FINISHED":
        return "ready"
    if status == "IN_PROGRESS":
        return "pending"
    if status in ("ERROR", "EXPIRED"):
        return "failed"
    return "already_published"

def require_all_ready(container_ids, responses):
    if not isinstance(container_ids, list) or not container_ids or len(set(container_ids)) != len(container_ids):
        raise ContainerStatusError("container IDs missing or duplicated")
    if not isinstance(responses, list) or len(responses) != len(container_ids):
        raise ContainerStatusError("one status response required per container")
    statuses = [classify_container_status(cid, response) for cid, response in zip(container_ids, responses)]
    if any(status != "ready" for status in statuses):
        raise ContainerStatusError("all containers must be FINISHED before continuing")
    return True
