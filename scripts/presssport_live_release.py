"""Production entrypoint. Fail-closed until a separate, fresh Paolo Savio approval.

Never runs automatically. The GitHub workflow must be explicitly dispatched and
the immutable approved manifest, exact account, and authorization must all match.
Meta POST is handled only by the existing one-attempt publication orchestrator.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from scripts.check_publication_authorization import validate
from scripts.presssport_executor_boundary import execute_authorized
from scripts.meta_identity_readonly import verify_identity
from scripts.presssport_media_preflight import verify_media
from scripts.presssport_meta_transport import MetaGraphTransport

MANIFEST = Path("publishing/presssport-2026-10-28.json")
AUTHORIZATION = Path("publishing/presssport-2026-10-28-authorization.json")

def run_release(manifest_bytes, authorization, *, publish_now, confirm_account,
                confirm_sha256, token, database_url, db_connect,
                media_check=verify_media, identity_check=verify_identity,
                meta_factory=MetaGraphTransport, now=None):
    """Validate all conditions before creating a DB connection or any Meta POST."""
    if publish_now is not True:
        raise PermissionError("live publish disabled; explicit publish_now required")
    if not isinstance(authorization, dict) or authorization.get("action") != "publish_now":
        raise PermissionError("separate immediate publication approval required")
    manifest = json.loads(manifest_bytes)
    account = manifest.get("instagram_account_id")
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    if confirm_account != account or confirm_sha256 != digest:
        raise PermissionError("release confirmation does not match exact account and manifest")
    blockers = validate(manifest_bytes, authorization, now=now)
    if blockers:
        raise PermissionError("; ".join(blockers))
    if not isinstance(token, str) or not token or not isinstance(database_url, str) or not database_url:
        raise ValueError("cloud credentials are required for authorized publishing")
    if db_connect is None:
        raise ValueError("server-side PostgreSQL connector required")

    media = media_check(manifest_bytes)
    if not isinstance(media, dict) or media.get("all_reachable") is not True or media.get("image_count") != len(manifest["image_urls"]):
        raise RuntimeError("public carousel images not verified; publication blocked")

    # execute_authorized revalidates authorization, checks Meta account identity
    # before DB creation and closes the connection under success or failure.
    return execute_authorized(
        manifest_bytes, authorization,
        verify=lambda payload: identity_check(payload, token),
        connect=lambda: db_connect(database_url, sslmode="require", connect_timeout=10),
        make_meta=lambda: meta_factory(token),
        now=now,
    )

def main(argv=None):
    parser=argparse.ArgumentParser(description="Explicitly authorized live Instagram carousel release")
    parser.add_argument("--publish-now", action="store_true", help="Required explicit release action")
    parser.add_argument("--confirm-account", required=True)
    parser.add_argument("--confirm-manifest-sha256", required=True)
    args=parser.parse_args(argv)
    if os.environ.get("PRESSSPORT_ENABLE_LIVE_PUBLISH") != "YES":
        raise PermissionError("live release disabled by server-side environment gate")
    manifest_bytes=MANIFEST.read_bytes()
    auth=json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    # Validate locally before even importing the DB driver or loading tokens.
    digest=hashlib.sha256(manifest_bytes).hexdigest()
    account=json.loads(manifest_bytes)["instagram_account_id"]
    if not args.publish_now or args.confirm_account != account or args.confirm_manifest_sha256 != digest:
        raise PermissionError("explicit account and exact manifest confirmation required")
    blockers=validate(manifest_bytes, auth)
    if blockers:
        raise PermissionError("; ".join(blockers))
    import psycopg
    result=run_release(
        manifest_bytes, auth, publish_now=True,
        confirm_account=args.confirm_account,
        confirm_sha256=args.confirm_manifest_sha256,
        token=os.environ.get("META_INSTAGRAM_ACCESS_TOKEN", ""),
        database_url=os.environ.get("PRESSSPORT_DATABASE_URL", ""),
        db_connect=psycopg.connect,
    )
    print(json.dumps({"state": result["state"], "media_id": result["media_id"]}, sort_keys=True))

if __name__=="__main__":
    main()
