"""Press & Sport Cloud multichannel editorial manifest validation (offline only).

This module never publishes, schedules a job, or grants publication authorization.
Approval and release are distinct operations managed by separate services.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit

INSTAGRAM_ACCOUNT = "17841425937268080"
LINKEDIN_ORGANIZATION = "146625659"
TRUSTED_HOST = "pressandsport.it"
KINDS = {
    "instagram_image": (1, 1),
    "instagram_carousel": (2, 10),
    "instagram_story": (1, 1),
    "linkedin_image": (1, 1),
}
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,78}[a-z0-9]$")
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")


def validate_manifest(*, post_key: str, kind: str, caption: str,
                      image_urls: list[str], account_id: str) -> dict:
    """Return an immutable, hashed manifest; never authorize publication."""
    if not isinstance(post_key, str) or not KEY_RE.fullmatch(post_key):
        raise ValueError("invalid post_key")
    if kind not in KINDS:
        raise ValueError("unsupported content type")
    expected_account = LINKEDIN_ORGANIZATION if kind == "linkedin_image" else INSTAGRAM_ACCOUNT
    if account_id != expected_account:
        raise ValueError("account does not match content type")
    if not isinstance(caption, str) or len(caption.strip()) > (3000 if kind == "linkedin_image" else 2200):
        raise ValueError("invalid caption")
    if kind != "instagram_story" and not caption.strip():
        raise ValueError("caption required")
    low, high = KINDS[kind]
    if not isinstance(image_urls, list) or not low <= len(image_urls) <= high:
        raise ValueError("wrong image count")
    if any(not isinstance(url, str) for url in image_urls) or len(set(image_urls)) != len(image_urls):
        raise ValueError("invalid or duplicate image URLs")
    for url in image_urls:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname != TRUSTED_HOST
                or parsed.port is not None or parsed.username or parsed.password
                or parsed.query or parsed.fragment
                or not parsed.path.lower().endswith((".jpg", ".jpeg"))):
            raise ValueError("images must be public HTTPS JPEGs on pressandsport.it")
    payload = {
        "post_key": post_key, "kind": kind, "account_id": account_id,
        "caption": caption.strip(), "image_urls": list(image_urls),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":")).encode("utf-8")
    return {**payload, "content_sha256": hashlib.sha256(serialized).hexdigest(),
            "publication_authorized": False}


def verify_release(manifest: dict, *, approved_digest: str, approved_account: str,
                   explicit_authorization: bool) -> bool:
    """Fail closed if a separately approved release does not match exactly.

    This is a guard, not a publication or authorization-issuing function.
    A production publisher must also enforce single-use ledger reservation.
    """
    if not explicit_authorization or not isinstance(approved_digest, str) or not DIGEST_RE.fullmatch(approved_digest):
        return False
    return (manifest.get("content_sha256") == approved_digest
            and manifest.get("account_id") == approved_account)
