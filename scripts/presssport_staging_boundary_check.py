"""Offline staging validation of the executor boundary using blocked authorization.

No credentials, database connections or Meta API requests.
"""
import json
from pathlib import Path
from scripts.presssport_executor_boundary import execute_authorized

MANIFEST=Path("publishing/presssport-2026-10-28.json")
AUTH=Path("publishing/presssport-2026-10-28-authorization.json")

def verify_boundary():
    manifest=MANIFEST.read_bytes()
    authorization=json.loads(AUTH.read_text(encoding="utf-8"))
    attempts=[]
    def forbidden(*args,**kwargs):
        attempts.append("external")
        raise AssertionError("external dependency must not be initialized")
    try:
        execute_authorized(manifest,authorization,
                           verify=forbidden,connect=forbidden,make_meta=forbidden)
    except PermissionError:
        if attempts:
            raise AssertionError("authorization gate opened an external dependency")
        return {"authorization_blocked":True,"external_calls":0,"published":False}
    raise AssertionError("disabled authorization unexpectedly accepted")
