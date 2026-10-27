#!/usr/bin/env python3
"""Read-only verification of the seven public JPEGs for the 2026-10-28 carousel."""
import json
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image

BASE = "https://pressandsport.it/instagram-media/2026-10-28"
results = []
for index in range(1, 8):
    name = f"PressSport_Carosello_Slide_{index:02d}_di_07.jpg"
    url = f"{BASE}/{name}"
    record = {"slide": index, "url": url, "ok": False}
    try:
        req = Request(url, headers={"User-Agent": "PressSport-Carousel-Check/1.0"})
        with urlopen(req, timeout=25) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(15 * 1024 * 1024 + 1)
            record["http_status"] = response.status
            record["content_type"] = content_type
        if len(data) > 15 * 1024 * 1024:
            raise ValueError("Image exceeds 15 MB")
        with Image.open(BytesIO(data)) as img:
            record["format"] = img.format
            record["dimensions"] = list(img.size)
            img.verify()
        if record["format"] != "JPEG" or record["dimensions"] != [1080, 1350]:
            raise ValueError("Unexpected format or dimensions")
        if not content_type.lower().startswith("image/jpeg"):
            raise ValueError("Unexpected Content-Type")
        record["ok"] = True
    except Exception as exc:
        record["error"] = str(exc)
    results.append(record)
    print(f"{'PASS' if record['ok'] else 'FAIL'}: {name}")

report = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "ready": all(r["ok"] for r in results),
    "slides": results,
    "publication_performed": False,
}
Path("carousel-verification-report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print("READY" if report["ready"] else "NOT READY")
sys.exit(0 if report["ready"] else 1)
