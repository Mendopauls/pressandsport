#!/usr/bin/env python3
"""Read-only Meta Graph status transport; no publishing or database writes."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from scripts.meta_container_status import status_request, classify_container_status

class MetaStatusUnavailable(RuntimeError):
    pass

def get_container_status(container_id, *, access_token, api_version="v24.0", opener=urlopen, timeout=15):
    descriptor = status_request(container_id)
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("Meta token required")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+", api_version):
        raise ValueError("invalid Graph version")
    params = dict(descriptor["params"])
    params["access_token"] = access_token
    url = "https://graph.facebook.com/" + api_version + descriptor["path"] + "?" + urlencode(params)
    request = Request(url, method="GET")
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read()
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise MetaStatusUnavailable("Meta status request failed; do not proceed") from exc
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise MetaStatusUnavailable("invalid Meta status response") from exc
    try:
        classification = classify_container_status(container_id, payload)
    except (ValueError, TypeError) as exc:
        raise MetaStatusUnavailable("untrusted Meta container status") from exc
    return {"container_id": container_id, "classification": classification}
