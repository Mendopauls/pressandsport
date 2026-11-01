"""Authenticated read-only editorial API (stdlib WSGI).

NO publish routes. Use a trusted HTTPS reverse proxy, rate limiting and a
private server runtime. Auth token is verified via Supabase Auth /user; operator
allowlist is checked against the private database, never user_metadata.
"""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from scripts.presssport_multichannel_queue import list_queue

def verified_email(token, supabase_url, publishable_key, opener=urlopen):
    if not isinstance(token, str) or not token or len(token) > 8192:
        return None
    url = urlsplit(supabase_url)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        return None
    request = Request(supabase_url.rstrip("/") + "/auth/v1/user", headers={
        "Authorization": "Bearer " + token,
        "apikey": publishable_key,
        "Accept": "application/json",
    })
    try:
        with opener(request, timeout=8) as response:
            if response.status != 200:
                return None
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
        return None
    email = data.get("email") if isinstance(data, dict) else None
    return email.strip().lower() if isinstance(email, str) and email.strip() else None

def is_operator(connection, email):
    if not email:
        return False
    with connection.cursor() as cur:
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM presssport_internal.admin_allowlist "
            "WHERE lower(trim(email)) = %s)", (email,))
        return bool(cur.fetchone()[0])

def handle_request(method, path, authorization, *, db_connect,
                   supabase_url, publishable_key, verifier=verified_email):
    if path != "/api/editorial/v2/queue":
        return 404, {"error": "not_found"}
    if method != "GET":
        return 405, {"error": "method_not_allowed"}
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        return 401, {"error": "unauthorized"}
    token = authorization[7:].strip()
    email = verifier(token, supabase_url, publishable_key)
    if not email:
        return 401, {"error": "unauthorized"}
    with db_connect() as connection:
        if not is_operator(connection, email):
            return 403, {"error": "forbidden"}
        items = list_queue(connection)
    return 200, {"items": items, "read_only": True, "publication_authorized": False}

def application(environ, start_response):
    """Deployment requires PRESSSPORT_DATABASE_URL and Supabase Auth settings."""
    try:
        import psycopg
        config = (os.environ["PRESSSPORT_DATABASE_URL"],
                  os.environ["PRESSSPORT_SUPABASE_URL"],
                  os.environ["PRESSSPORT_SUPABASE_PUBLISHABLE_KEY"])
        status, payload = handle_request(
            environ.get("REQUEST_METHOD", ""), environ.get("PATH_INFO", ""),
            environ.get("HTTP_AUTHORIZATION"),
            db_connect=lambda: psycopg.connect(config[0], connect_timeout=8),
            supabase_url=config[1], publishable_key=config[2])
    except Exception:
        status, payload = 503, {"error": "service_unavailable"}
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    labels = {200: "OK", 401: "Unauthorized", 403: "Forbidden",
              404: "Not Found", 405: "Method Not Allowed",
              503: "Service Unavailable"}
    start_response(f"{status} {labels[status]}", [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(raw))),
        ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")])
    return [raw]
