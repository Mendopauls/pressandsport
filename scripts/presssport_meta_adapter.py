#!/usr/bin/env python3
"""Injectable Meta adapter for the publication orchestrator.

Does not execute anything when imported. Only an explicitly authorized caller
can invoke POST methods. Container status is GET-only and never retried.
"""
from scripts.meta_graph_transport import post_graph
from scripts.meta_graph_status_transport import get_container_status

class MetaAdapter:
    def __init__(self, access_token, *, post=post_graph, get=get_container_status):
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Meta access token required")
        self._token = access_token
        self._post = post
        self._get = get

    def post(self, descriptor):
        return self._post(descriptor, access_token=self._token)

    def status(self, container_id):
        result = self._get(container_id, access_token=self._token)
        # The orchestrator consumes the canonical Meta status response.
        # Do not fabricate FINISHED from an unavailable or ambiguous status.
        classification = result.get("classification")
        if result.get("container_id") != container_id:
            raise RuntimeError("Meta container identity mismatch")
        status_codes = {"ready": "FINISHED", "pending": "IN_PROGRESS",
                        "failed": "ERROR", "already_published": "PUBLISHED"}
        if classification not in status_codes:
            raise RuntimeError("unknown Meta container classification")
        return {"id": container_id, "status_code": status_codes[classification]}
