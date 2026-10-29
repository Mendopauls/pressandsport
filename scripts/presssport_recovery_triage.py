#!/usr/bin/env python3
"""Conservative publication recovery decisions, without any Meta POST or DB write.

A missing media ID does not prove that Meta did not publish. Never authorize
an automatic retry from a stalled or uncertain ledger row.
"""

KNOWN_STATES = frozenset({"reserved", "publishing", "uncertain", "published", "failed", "cancelled"})

def recovery_decision(state, *, reconciliation_required=False, stale=False, media_id=None):
    if state not in KNOWN_STATES:
        return {"action": "block", "reason": "unknown ledger state"}
    if state == "published":
        if not isinstance(media_id, str) or not media_id.isdecimal():
            return {"action": "manual_review", "reason": "published row missing valid media ID"}
        return {"action": "no_retry", "reason": "publication already recorded"}
    if state == "uncertain" or reconciliation_required:
        return {"action": "manual_review", "reason": "ambiguous Meta outcome; independent verification required"}
    if state == "publishing":
        return {"action": "manual_review" if stale else "wait",
                "reason": "publishing may have reached Meta; never automatically retry"}
    if state == "reserved":
        return {"action": "manual_review" if stale else "wait",
                "reason": "reservation exists; do not start a second attempt"}
    return {"action": "no_retry", "reason": "terminal reservation; no automatic retry"}

def recovery_report(entries):
    """Return conservative decisions for diagnostic rows, never retry directives."""
    if not isinstance(entries, list):
        raise ValueError("entries must be a list")
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid ledger entry")
        decision = recovery_decision(
            entry.get("state"),
            reconciliation_required=entry.get("reconciliation_required", False),
            stale=entry.get("stale_publishing", False),
            media_id=entry.get("meta_media_id"))
        result.append({"publication_key": entry.get("publication_key"), **decision})
    return result
