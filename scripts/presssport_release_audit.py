#!/usr/bin/env python3
"""Fail-closed cloud publisher release audit. No network, secrets, DB writes or Meta calls."""
import importlib
import json
from pathlib import Path

REQUIRED = {
    "scripts.check_publication_authorization": "validate",
    "scripts.prepublish_guard": "prepare_reservation",
    "scripts.publication_reservation": "reserve_publication",
    "scripts.publication_state_db": "transition_reservation",
    "scripts.meta_carousel_requests": "publish_request",
    "scripts.meta_graph_transport": "post_graph",
    "scripts.meta_graph_status_transport": "get_container_status",
    "scripts.meta_identity_readonly": "verify_identity",
}
MANIFEST = Path("publishing/presssport-2026-10-28.json")
AUTH = Path("publishing/presssport-2026-10-28-authorization.json")

def audit():
    missing = []
    for module, name in REQUIRED.items():
        try:
            if not callable(getattr(importlib.import_module(module), name)):
                missing.append(module + "." + name)
        except (ImportError, AttributeError):
            missing.append(module + "." + name)
    manifest = json.loads(MANIFEST.read_bytes())
    authorization = json.loads(AUTH.read_bytes())
    if authorization.get("publish_authorized") is not False:
        raise RuntimeError("release audit requires publishing disabled")
    if manifest.get("status") != "approved":
        raise RuntimeError("manifest not editorially approved")
    if len(manifest.get("image_urls", [])) != 7:
        raise RuntimeError("expected seven carousel images")
    from scripts.check_publication_authorization import validate
    if not validate(MANIFEST.read_bytes(), authorization):
        raise RuntimeError("publication gate unexpectedly open")
    # A fully wired production runner must be separately audited before release.
    runner = Path("scripts/presssport_cloud_publisher.py").exists()
    return {"components_present": len(REQUIRED) - len(missing),
            "components_required": len(REQUIRED),
            "missing_components": missing,
            "production_runner_present": runner,
            "publication_authorized": False,
            "release_ready": not missing and runner}

def main():
    result = audit()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["missing_components"]:
        raise SystemExit(1)
    print("PASS: component audit complete; release readiness reported separately")
    print("PUBLICATION: NOT PERFORMED")

if __name__ == "__main__":
    main()
