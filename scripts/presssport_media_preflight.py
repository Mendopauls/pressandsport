"""Read-only public-image preflight. No Meta or database access.

Checks that each approved carousel URL serves JPEG image bytes over HTTPS.
This cannot establish that Meta has fetched or approved the media.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from scripts.meta_carousel_plan import plan_carousel

MANIFEST = Path("publishing/presssport-2026-10-28.json")
MAX_IMAGE_BYTES = 20_000_000
EXPECTED_HOST = "pressandsport.it"

def verify_media(manifest_bytes, *, opener=urlopen, max_bytes=MAX_IMAGE_BYTES):
    plan = plan_carousel(manifest_bytes)
    urls = [child["image_url"] for child in plan["children"]]
    if len(set(urls)) != len(urls):
        raise ValueError("duplicate carousel image URL")
    results = []
    for index, url in enumerate(urls, start=1):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != EXPECTED_HOST or parsed.port is not None:
            raise ValueError(f"slide {index}: unexpected public media host")
        request = Request(url, headers={"User-Agent": "PressSport-ReadOnlyMediaPreflight/1.0"}, method="GET")
        try:
            with opener(request, timeout=20) as response:
                resolved = urlsplit(response.geturl())
                if resolved.scheme != "https" or resolved.hostname != EXPECTED_HOST:
                    raise ValueError("media redirects away from approved public host")
                if response.status != 200:
                    raise ValueError("unexpected media HTTP status")
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type not in ("image/jpeg", "image/jpg"):
                    raise ValueError("wrong media MIME type")
                content = response.read(max_bytes + 1)
        except Exception as exc:
            raise RuntimeError(f"slide {index}: media unavailable or invalid") from exc
        if not (4 <= len(content) <= max_bytes and content.startswith(b"\\xff\\xd8\\xff") and content.endswith(b"\\xff\\xd9")):
            raise ValueError(f"slide {index}: invalid or excessive JPEG payload")
        results.append({"slide": index, "reachable": True, "mime": "image/jpeg", "size_bytes": len(content)})
    return {"all_reachable": True, "image_count": len(results), "slides": results, "publication_performed": False}

def main():
    import json as _json
    print(_json.dumps(verify_media(MANIFEST.read_bytes()), indent=2))

if __name__ == "__main__":
    main()
