#!/usr/bin/env python3
"""Pure, offline ledger state validation. Does not publish or modify files."""
import hashlib
import json
from datetime import datetime

ACTIVE = {"reserved", "publishing", "published", "uncertain"}
TERMINAL = {"cancelled", "failed"}
ALLOWED = ACTIVE | TERMINAL

def publication_key(account, urls):
    payload = json.dumps({"account": account, "urls": urls}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def validate_ledger(entries):
    if not isinstance(entries, list):
        return ["ledger must be a list"]
    problems = []
    active_keys = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"entry {index}: must be object")
            continue
        account, urls, status = entry.get("instagram_account_id"), entry.get("image_urls"), entry.get("status")
        if not isinstance(account, str) or not account or not isinstance(urls, list) or not urls or any(not isinstance(url, str) or not url for url in urls):
            problems.append(f"entry {index}: invalid account or media")
            continue
        if status not in ALLOWED:
            problems.append(f"entry {index}: unknown status")
            continue
        key = publication_key(account, urls)
        if entry.get("publication_key") != key:
            problems.append(f"entry {index}: missing or mismatched publication key")
        if status in ACTIVE:
            if key in active_keys:
                problems.append(f"entry {index}: duplicate active publication key")
            active_keys.add(key)
        if status in {"publishing", "published", "uncertain"} and not entry.get("attempt_id"):
            problems.append(f"entry {index}: attempt ID missing")
        if status == "published" and not entry.get("meta_media_id"):
            problems.append(f"entry {index}: Meta media ID missing")
        if status == "uncertain" and not entry.get("reconciliation_required"):
            problems.append(f"entry {index}: uncertain result requires reconciliation")
    return problems

def duplicate_blockers(manifest, entries):
    problems = validate_ledger(entries)
    if problems:
        return problems
    key = publication_key(manifest["instagram_account_id"], manifest["image_urls"])
    if any(entry.get("publication_key") == key and entry.get("status") in ACTIVE for entry in entries):
        return ["matching publication is reserved, publishing, published or uncertain"]
    return []

# State changes are intentionally restrictive. A timed-out publish must
# remain uncertain until a separate reconciliation procedure confirms outcome.
TRANSITIONS = {
    "reserved": {"publishing", "cancelled"},
    "publishing": {"published", "uncertain"},
    "uncertain": {"published", "failed"},
    "published": set(),
    "cancelled": set(),
    "failed": set(),
}

def validate_transition(previous, next_status, *, reconciled=False):
    """Return a list of blockers for a proposed state transition."""
    problems = []
    old = previous.get("status")
    if old not in TRANSITIONS or next_status not in ALLOWED:
        return ["unknown publication status"]
    if next_status not in TRANSITIONS[old]:
        problems.append("transition not permitted")
    if old == "uncertain" and next_status == "failed" and not reconciled:
        problems.append("uncertain result requires confirmed reconciliation")
    if old == "publishing" and next_status == "published" and not previous.get("attempt_id"):
        problems.append("publication attempt identifier missing")
    return problems
