"""Explicitly injectable Meta Graph transport. No credentials, CLI or live entrypoint.

A POST is never retried: network uncertainty must be reconciled manually.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GRAPH_BASE = "https://graph.facebook.com/v24.0"

class MetaGraphTransport:
    def __init__(self, token, *, opener=urlopen):
        if not isinstance(token, str) or not token:
            raise ValueError("missing access token")
        self._token = token
        self._opener = opener

    def _request(self, method, path, params):
        if not isinstance(path, str) or not path.startswith("/") or "?" in path or ".." in path:
            raise ValueError("invalid Meta path")
        fields = dict(params)
        fields["access_token"] = self._token
        if method == "POST":
            req = Request(GRAPH_BASE + path, data=urlencode(fields).encode("utf-8"), method="POST")
        elif method == "GET":
            req = Request(GRAPH_BASE + path + "?" + urlencode(fields), method="GET")
        else:
            raise ValueError("unsupported HTTP method")
        try:
            with self._opener(req, timeout=30) as response:
                result = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise RuntimeError("Meta request failed; outcome may be uncertain; do not retry") from exc
        if not isinstance(result, dict) or "error" in result:
            raise RuntimeError("Meta response rejected; do not retry")
        return result

    def post(self, request):
        if not isinstance(request, dict) or request.get("method") != "POST":
            raise ValueError("invalid Meta POST contract")
        path = request.get("path")
        if not isinstance(path, str) or not (path.endswith("/media") or path.endswith("/media_publish")):
            raise ValueError("unsupported Meta POST path")
        result = self._request("POST", path, request.get("form") or {})
        identifier = result.get("id")
        if not isinstance(identifier, str) or not identifier.isdecimal():
            raise RuntimeError("invalid Meta POST identifier; do not retry")
        return identifier

    def status(self, container_id):
        if not isinstance(container_id, str) or not container_id.isdecimal():
            raise ValueError("invalid container ID")
        return self._request("GET", "/" + container_id, {"fields": "id,status_code"})
