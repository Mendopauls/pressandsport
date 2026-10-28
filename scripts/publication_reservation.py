#!/usr/bin/env python3
"""Database reservation primitive. No Meta API calls and no credential handling."""
import hashlib
import json
import uuid
from scripts.publication_ledger_state import publication_key

INSERT_RESERVATION = """
INSERT INTO presssport_internal.publication_reservations
(publication_key, instagram_account_id, manifest_sha256, attempt_id)
VALUES (%s, %s, %s, %s)
RETURNING publication_key
"""

def reserve_publication(connection, manifest_bytes, attempt_id=None):
    """Atomically reserve an approved manifest using an existing DB connection.

    Caller MUST validate fresh, explicit authorization and identity first.
    Caller MUST commit before contacting Meta. A uniqueness conflict must
    propagate and fail closed; do not use ON CONFLICT DO NOTHING or retry.
    """
    manifest = json.loads(manifest_bytes)
    if manifest.get("status") != "approved":
        raise ValueError("editorial approval missing")
    account = manifest.get("instagram_account_id")
    urls = manifest.get("image_urls")
    if not isinstance(account, str) or not account:
        raise ValueError("invalid Instagram account")
    if not isinstance(urls, list) or not urls or any(not isinstance(u, str) or not u.startswith("https://") for u in urls):
        raise ValueError("invalid media URLs")
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    key = publication_key(account, urls)
    attempt = str(uuid.UUID(str(attempt_id))) if attempt_id else str(uuid.uuid4())
    with connection.cursor() as cursor:
        cursor.execute(INSERT_RESERVATION, (key, account, digest, attempt))
        result = cursor.fetchone()
    if not result or result[0] != key:
        raise RuntimeError("reservation was not confirmed")
    return {"publication_key": key, "attempt_id": attempt, "manifest_sha256": digest}
