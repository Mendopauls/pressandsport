"""Dependency-injected execution boundary; no network or CLI entrypoint.

The caller supplies identity verification, database connection, and Meta adapter.
No live credentials are read here. Authorization must pass before any dependency
that could create external side effects is initialized.
"""
import json
from scripts.check_publication_authorization import validate
from scripts.presssport_publication_orchestrator import execute_once

def execute_authorized(manifest_bytes, authorization, *, verify, connect, make_meta, now=None):
    if not isinstance(authorization, dict) or authorization.get("action") != "publish_now":
        raise PermissionError("explicit immediate publication authorization required")
    problems=validate(manifest_bytes,authorization,now=now)
    if problems:
        raise PermissionError("; ".join(problems))
    account=json.loads(manifest_bytes).get("instagram_account_id")
    identity=verify(manifest_bytes)
    if not isinstance(identity,dict) or identity.get("verified") is not True or identity.get("account_id") != account:
        raise PermissionError("Instagram account identity not verified")
    connection=connect()
    try:
        meta=make_meta()
        return execute_once(connection,manifest_bytes,authorization,meta,identity_verified=True,now=now)
    finally:
        connection.close()
