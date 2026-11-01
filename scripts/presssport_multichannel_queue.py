"""DB operations for private multichannel editorial queue; no posting capabilities.

Caller MUST authenticate operator and connect to restricted internal database role
server-side. Never expose this module as an unauthenticated HTTP endpoint.
"""
from datetime import datetime, timezone
import json
from scripts.presssport_multichannel_manifest import validate_manifest

TRANSITIONS = {
    ("draft", "ready_for_review"),
    ("ready_for_review", "draft"),
    ("ready_for_review", "approved"),
    ("approved", "planned"),
    ("planned", "approved"),
    ("draft", "cancelled"),
    ("ready_for_review", "cancelled"),
    ("approved", "cancelled"),
    ("planned", "cancelled"),
}

def insert_draft(connection, *, post_key, kind, caption, image_urls, account_id):
    manifest = validate_manifest(post_key=post_key, kind=kind,
                                 caption=caption, image_urls=image_urls,
                                 account_id=account_id)
    channel = "linkedin" if kind == "linkedin_image" else "instagram"
    with connection.cursor() as cur:
        cur.execute(
            """INSERT INTO presssport_internal.multichannel_queue
               (post_key, channel, content_kind, account_id, caption,
                image_urls, content_sha256)
               VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)
               RETURNING post_key, editorial_state""",
            (post_key, channel, kind, account_id, manifest["caption"],
             json.dumps(manifest["image_urls"]), manifest["content_sha256"]))
        row = cur.fetchone()
    if row != (post_key, "draft"):
        raise RuntimeError("unexpected draft insert result")
    return {"post_key": row[0], "editorial_state": row[1],
            "publication_authorized": False}

def move_state(connection, *, post_key, from_state, to_state,
               operator, planned_at=None, now=None):
    if (from_state, to_state) not in TRANSITIONS:
        raise ValueError("invalid editorial transition")
    if to_state == "approved" and from_state == "ready_for_review" and operator != "Paolo Savio":
        raise PermissionError("editorial approval must be recorded by Paolo Savio")
    if to_state == "planned":
        current = now or datetime.now(timezone.utc)
        if (not isinstance(planned_at, datetime) or planned_at.tzinfo is None
                or planned_at <= current):
            raise ValueError("future, timezone-aware date required")
    with connection.cursor() as cur:
        cur.execute(
            """UPDATE presssport_internal.multichannel_queue
               SET editorial_state=%s,
                   approved_by=CASE WHEN %s='approved' AND %s='ready_for_review'
                                    THEN %s ELSE approved_by END,
                   approved_at=CASE WHEN %s='approved' AND %s='ready_for_review'
                                    THEN now() ELSE approved_at END,
                   planned_at=CASE WHEN %s='planned' THEN %s::timestamptz
                                   WHEN %s='approved' THEN NULL ELSE planned_at END
               WHERE post_key=%s AND editorial_state=%s
               RETURNING post_key,editorial_state""",
            (to_state, to_state, from_state, operator, to_state, from_state,
             to_state, planned_at, to_state, post_key, from_state))
        row = cur.fetchone()
    if row != (post_key, to_state):
        raise RuntimeError("editorial item absent or concurrently updated")
    return {"post_key": row[0], "editorial_state": row[1],
            "publication_authorized": False}

def list_queue(connection):
    """For authorized server-side operators only; never a release instruction."""
    with connection.cursor() as cur:
        cur.execute(
            """SELECT post_key, channel, content_kind, account_id,
                      editorial_state, planned_at, content_sha256
               FROM presssport_internal.multichannel_queue
               ORDER BY created_at DESC, post_key DESC""")
        rows = cur.fetchall()
    return [
        {"post_key": r[0], "channel": r[1], "kind": r[2],
         "account_id": r[3], "state": r[4],
         "planned_at": r[5].isoformat() if r[5] else None,
         "digest": r[6], "publication_authorized": False}
        for r in rows
    ]
