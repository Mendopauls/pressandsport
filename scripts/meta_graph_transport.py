#!/usr/bin/env python3
"""Meta Graph API transport. No token storage, retries, or automatic publication.

Callers must complete authorization, reservation and committed state transitions
before invoking write endpoints. Any ambiguous response is fail-closed.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

class MetaTransportError(RuntimeError):
    """An API request failed; caller must classify the attempt conservatively."""

class MetaOutcomeUncertain(MetaTransportError):
    """Network failure or invalid response: never retry a publish automatically."""

def post_graph(request, *, access_token, api_version="v24.0", opener=urlopen, timeout=30):
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("Meta token required")
    if request.get("method") != "POST":
        raise ValueError("only POST requests supported")
    path = request.get("path")
    if not isinstance(path, str) or not path.startswith("/") or "//" in path or "?" in path:
        raise ValueError("invalid Graph path")
    if not api_version.startswith("v") or not api_version[1:].replace(".", "").isdigit():
        raise ValueError("invalid Graph API version")
    form = request.get("form")
    if not isinstance(form, dict) or not form:
        raise ValueError("request form missing")
    fields = {**form, "access_token": access_token}
    body = urlencode(fields).encode("utf-8")
    url = "https://graph.facebook.com/" + api_version + path
    http_request = Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with opener(http_request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        # Meta errors may follow an already-accepted write. No automatic retries.
        raise MetaOutcomeUncertain("Meta HTTP error; reconcile before retry") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise MetaOutcomeUncertain("Meta network outcome uncertain; reconcile before retry") from exc
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise MetaOutcomeUncertain("Meta response could not be parsed") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("id"), str) or not payload["id"]:
        raise MetaOutcomeUncertain("Meta response missing object ID")
    return payload["id"]
