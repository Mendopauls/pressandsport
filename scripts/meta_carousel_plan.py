#!/usr/bin/env python3
"""Pure Meta carousel request planning. Does not contact Meta or publish."""
import json
from urllib.parse import urlparse

def plan_carousel(manifest_bytes):
    manifest = json.loads(manifest_bytes)
    if manifest.get("status") != "approved":
        raise ValueError("editorial approval missing")
    account = manifest.get("instagram_account_id")
    caption = manifest.get("caption")
    urls = manifest.get("image_urls")
    if not isinstance(account, str) or not account.isdecimal():
        raise ValueError("invalid Instagram account")
    if not isinstance(caption, str) or not caption.strip():
        raise ValueError("caption missing")
    if not isinstance(urls, list) or not 2 <= len(urls) <= 10:
        raise ValueError("carousel requires 2-10 images")
    for url in urls:
        if not isinstance(url, str):
            raise ValueError("invalid media URL")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("invalid HTTPS media URL")
    return {
        "instagram_account_id": account,
        "children": [{"image_url": url, "is_carousel_item": "true"} for url in urls],
        "parent": {"media_type": "CAROUSEL", "caption": caption},
        "publish": {"requires_explicit_authorization": True},
    }
