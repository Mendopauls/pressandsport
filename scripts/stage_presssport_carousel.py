#!/usr/bin/env python3
"""Download approved carousel images from a Google Drive folder via a service account.
Requires GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON GitHub Actions secret and Drive folder shared
with the service-account email. Does not publish to Instagram.
"""
import io
import json
import os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image

FOLDER_ID = "19T4NI6iiz8ykbQhieVJXQSW5DnVnos_7"
FILES = [
    ("1MNO70XEgoYjFPCt_l9PYxVbUGzCEo2ip", "PressSport_Carosello_Slide_01_di_07.png"),
    ("1aU5TNZSSvGdFem_dkG33LsSOJTYwuU9Y", "PressSport_Carosello_Slide_02_di_07.png"),
    ("1lZZENGq1HuXVIKcBUcpP4Xr1uiQiKy-y", "PressSport_Carosello_Slide_03_di_07.png"),
    ("1mxz_t_sGTNM9Uqd7g8ul5_7n3M8ugUaR", "PressSport_Carosello_Slide_04_di_07.png"),
    ("1kOvSLgpB05JgtFFT7wBDmo97-xQWBuoO", "PressSport_Carosello_Slide_05_di_07.png"),
    ("1gOepop_zRQD6xJMMlgXlYiK9Q7sddae9", "PressSport_Carosello_Slide_06_di_07.png"),
    ("1KLuYXBOLvlovIf5e0AkJBSzJBLTvX52n", "PressSport_Carosello_Slide_07_di_07.png"),
]
secret = os.environ.get("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
if not secret:
    raise SystemExit("Missing GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON GitHub Actions secret")
creds = service_account.Credentials.from_service_account_info(
    json.loads(secret),
    scopes=["https://www.googleapis.com/auth/drive.readonly"],
)
service = build("drive", "v3", credentials=creds, cache_discovery=False)
out = Path("instagram-media/2026-10-28")
out.mkdir(parents=True, exist_ok=True)
for file_id, filename in FILES:
    metadata = service.files().get(fileId=file_id, fields="id,name,mimeType,parents").execute()
    if metadata.get("mimeType") != "image/png" or metadata.get("name") != filename:
        raise RuntimeError(f"Unexpected Drive metadata for {filename}: {metadata}")
    if FOLDER_ID not in metadata.get("parents", []):
        raise RuntimeError(f"Wrong Drive parent for {filename}")
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, service.files().get_media(fileId=file_id))
    done = False
    while not done:
        _, done = downloader.next_chunk()
    raw = buffer.getvalue()
    if not raw.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        raise RuntimeError(f"Not a PNG: {filename}")
    with Image.open(io.BytesIO(raw)) as img:
        if img.size != (1080, 1350):
            raise RuntimeError(f"Unexpected dimensions for {filename}: {img.size}")
        img.verify()
    (out / filename).write_bytes(raw)
    print(f"Verified {filename}: {len(raw)} bytes")
print("All 7 files verified; Instagram publication is NOT performed.")
