#!/usr/bin/env python3
"""Compare-and-swap state transitions for the private publication reservation ledger.

This module never calls Meta. Caller must commit successful transitions before
the next external side effect. Ambiguous outcomes require manual reconciliation.
"""
from scripts.publication_ledger_state import validate_transition

UPDATE_STATE = """
UPDATE presssport_internal.publication_reservations
SET state = %s, meta_media_id = %s, reconciliation_required = %s,
    updated_at = now()
WHERE publication_key = %s AND attempt_id = %s AND state = %s
RETURNING publication_key
"""

def transition_reservation(connection, *, publication_key, attempt_id,
                           from_state, to_state, meta_media_id=None,
                           reconciliation_required=False):
    if not publication_key or not attempt_id:
        raise ValueError("publication key and attempt id are required")
    if to_state == "published" and not meta_media_id:
        raise ValueError("published requires Meta media id")
    if to_state == "uncertain" and reconciliation_required is not True:
        raise ValueError("uncertain requires reconciliation")
    if to_state != "uncertain" and reconciliation_required:
        raise ValueError("reconciliation flag only valid for uncertain")
    if to_state != "published" and meta_media_id is not None:
        raise ValueError("Meta media id only accepted for published")
    problems = validate_transition({"status": from_state, "attempt_id": attempt_id}, to_state)\n    if problems:\n        raise ValueError("; ".join(problems))
    with connection.cursor() as cursor:
        cursor.execute(UPDATE_STATE, (to_state, meta_media_id,
                                      reconciliation_required, publication_key,
                                      attempt_id, from_state))
        row = cursor.fetchone()
    if row is None or row[0] != publication_key:
        raise RuntimeError("state transition conflict: do not retry publication")
    return {"publication_key": publication_key, "state": to_state}
