"""Reusable, server-side editorial queue. This module NEVER publishes.

Editorial approval and a planned date do not constitute Meta publication
authorization. A future authenticated publisher must obtain a separate explicit
authorization per exact manifest, and use the one-shot reservation ledger.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

ACCOUNT = "17841425937268080"
HOST = "pressandsport.it"
KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,78}[a-z0-9]$")

def normalized_post(post_key, caption, image_urls, *, account=ACCOUNT):
    if not isinstance(post_key, str) or not KEY_PATTERN.fullmatch(post_key):
        raise ValueError("post_key must be a stable lowercase slug (4-80 chars)")
    if account != ACCOUNT:
        raise ValueError("Instagram account not configured for Press & Sport")
    if not isinstance(caption, str) or not 1 <= len(caption.strip()) <= 2200:
        raise ValueError("caption must contain 1-2200 characters")
    if not isinstance(image_urls, list) or not 2 <= len(image_urls) <= 10:
        raise ValueError("carousel requires 2-10 JPEG URLs")
    if any(not isinstance(url, str) for url in image_urls) or len(set(image_urls)) != len(image_urls):
        raise ValueError("duplicate or invalid image URL")
    for url in image_urls:
        u = urlsplit(url)
        if (u.scheme != "https" or u.hostname != HOST or u.port is not None
                or u.username is not None or u.password is not None
                or u.query or u.fragment or not u.path.lower().endswith((".jpg", ".jpeg"))):
            raise ValueError("each image must be a public HTTPS JPEG on pressandsport.it")
    content = {"instagram_account_id": account, "caption": caption.strip(),
               "image_urls": list(image_urls)}
    canonical = json.dumps(content, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    return {"post_key": post_key, **content,
            "content_sha256": hashlib.sha256(canonical).hexdigest()}

def enqueue_draft(connection, post):
    """Create a draft; does not commit, authorize or initiate external I/O."""
    validated = normalized_post(post["post_key"], post["caption"], post["image_urls"],
                                account=post.get("instagram_account_id", ACCOUNT))
    with connection.cursor() as cur:
        cur.execute(
            """INSERT INTO presssport_internal.editorial_queue
               (post_key,instagram_account_id,caption,image_urls,content_sha256)
               VALUES (%s,%s,%s,%s::jsonb,%s)
               RETURNING post_key,editorial_state""",
            (validated["post_key"], validated["instagram_account_id"],
             validated["caption"], json.dumps(validated["image_urls"]),
             validated["content_sha256"]))
        row=cur.fetchone()
    if row != (validated["post_key"], "draft"):
        raise RuntimeError("editorial draft was not inserted")
    return {"post_key": row[0], "editorial_state": row[1],
            "publication_authorized": False}

def transition_editorial(connection, *, post_key, from_state, to_state,
                         approved_by=None, planned_at=None, now=None):
    """Optimistic-lock editorial transition. Never grants publishing rights."""
    allowed = {("draft","ready_for_review"),("ready_for_review","draft"),
               ("ready_for_review","approved"),("approved","planned"),
               ("planned","approved"),("draft","cancelled"),
               ("ready_for_review","cancelled"),("approved","cancelled"),
               ("planned","cancelled")}
    if (from_state,to_state) not in allowed:
        raise ValueError("editorial transition not permitted")
    if to_state == "approved" and from_state == "ready_for_review":
        if approved_by != "Paolo Savio":
            raise PermissionError("named editorial approval required")
    if to_state == "planned":
        at = planned_at
        timestamp = now or datetime.now(timezone.utc)
        if not isinstance(at,datetime) or at.tzinfo is None or at <= timestamp:
            raise ValueError("planned_at must be a future timezone-aware datetime")
    with connection.cursor() as cur:
        cur.execute(
            """UPDATE presssport_internal.editorial_queue
               SET editorial_state=%s,
                   approved_by=CASE WHEN %s='approved' AND %s='ready_for_review'
                                    THEN %s ELSE approved_by END,
                   approved_at=CASE WHEN %s='approved' AND %s='ready_for_review'
                                    THEN now() ELSE approved_at END,
                   planned_at=CASE WHEN %s='planned' THEN %s::timestamptz
                                   WHEN %s='approved' THEN NULL ELSE planned_at END,
                   updated_at=now()
               WHERE post_key=%s AND editorial_state=%s
               RETURNING post_key,editorial_state""",
            (to_state, to_state, from_state, approved_by, to_state, from_state,
             to_state, planned_at, to_state, post_key, from_state))
        result=cur.fetchone()
    if result != (post_key, to_state):
        raise RuntimeError("editorial state changed concurrently; do not retry blindly")
    return {"post_key": post_key, "editorial_state": to_state,
            "publication_authorized": False}

def inspect_due_plans(connection, *, now=None):
    """Read-only planning report; returning an item NEVER triggers publication."""
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    with connection.cursor() as cur:
        cur.execute(
            """SELECT post_key, content_sha256, planned_at
               FROM presssport_internal.editorial_queue
               WHERE editorial_state='planned' AND planned_at <= %s
               ORDER BY planned_at ASC, post_key ASC""", (timestamp,))
        rows = cur.fetchall()
    return [{"post_key": key, "content_sha256": digest,
             "planned_at": at.isoformat(), "publication_authorized": False,
             "action": "requires_separate_explicit_approval"}
            for key,digest,at in rows]
