#!/usr/bin/env python3
"""Injectable publication orchestrator; no CLI, credentials or automatic live execution.

The caller provides an already verified identity, a transaction-capable DB connection,
and a Meta adapter. All DB state changes are committed before Meta side effects.
Any failure after entering publishing is quarantined as uncertain, never retried.
"""
from scripts.prepublish_guard import prepare_reservation
from scripts.publication_state_db import transition_reservation
from scripts.meta_carousel_requests import child_requests, parent_request, publish_request
from scripts.meta_container_status import require_all_ready, classify_container_status

class PublicationUncertain(RuntimeError):
    pass

def execute_once(connection, manifest_bytes, authorization, meta, *,
                 identity_verified=False, now=None):
    reservation = prepare_reservation(connection, manifest_bytes, authorization,
                                      identity_verified=identity_verified, now=now)
    key, attempt = reservation["publication_key"], reservation["attempt_id"]
    connection.commit()  # Unique reservation durable before any external side effect.
    transition_reservation(connection, publication_key=key, attempt_id=attempt,
                           from_state="reserved", to_state="publishing")
    connection.commit()  # Publishing durable before any external side effect.
    try:
        children = [meta.post(req) for req in child_requests(manifest_bytes)]
        statuses = [meta.status(cid) for cid in children]
        require_all_ready(children, statuses)
        parent = meta.post(parent_request(manifest_bytes, children))
        if classify_container_status(parent, meta.status(parent)) != "ready":
            raise RuntimeError("parent container not ready")
        media_id = meta.post(publish_request(manifest_bytes, parent))
        if not isinstance(media_id, str) or not media_id.isdecimal():
            raise RuntimeError("invalid published media id")
    except Exception as exc:
        connection.rollback()
        try:
            transition_reservation(connection, publication_key=key, attempt_id=attempt,
                                   from_state="publishing", to_state="uncertain",
                                   reconciliation_required=True)
            connection.commit()
        except Exception as ledger_exc:
            connection.rollback()
            raise PublicationUncertain("Meta outcome uncertain; ledger reconciliation also failed") from ledger_exc
        raise PublicationUncertain("Meta outcome uncertain; manual reconciliation required") from exc
    try:
        transition_reservation(connection, publication_key=key, attempt_id=attempt,
                               from_state="publishing", to_state="published",
                               meta_media_id=media_id)
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise PublicationUncertain("Meta publish succeeded but ledger update failed; manual reconciliation required") from exc
    return {"state": "published", "media_id": media_id, **reservation}
