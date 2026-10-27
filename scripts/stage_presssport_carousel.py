#!/usr/bin/env python3
"""Stage seven explicitly approved Drive file IDs via keyless GitHub OIDC.
No Instagram publishing. Access is restricted by Drive sharing and OIDC policy.
"""
import io
from pathlib import Path
from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image

FILES = [
    ("1MNO70XEgoYjFPCt_l9PYxVbUGzCEo2ip", "PressSport_Carosello_Slide_01_di_07.png"),
    ("1aU5TNZSSvGdFem_dkG33LsSOJTYwuU9Y", "PressSport_Carosello_Slide_02_di_07.png"),
    ("1lZZENGq1HuXVIKcBUcpP4Xr1uiQiKy-y", "PressSport_Carosello_Slide_03_di_07.png"),
    ("1mxz_t_sGTNM9Uqd7g8ul5_7n3M8ugUaR", "PressSport_Carosello_Slide_04_di_07.png"),
    ("1kOvSLgpB05JgtFFT7wBDmo97-xQWBuoO", "PressSport_Carosello_Slide_05_di_07.png"),
    ("1gOepop_zRQD6xJMMlgXlYiK9Q7sddae9", "PressSport_Carosello_Slide_06_di_07.png"),
    ("1KLuYXBOLvlovIf5e0AkJBSzJBLTvX52n", "PressSport_Carosello_Slide_07_di_07.png"),
]
creds, _ = default(scopes=["https://www.googleapis.com/auth/drive.readonly"])
service = build("drive", "v3", credentials=creds, cache_discovery=False)
out = Path("instagram-media/2026-10-28")
out.mkdir(parents=True, exist_ok=True)
for file_id, filename in FILES:
    metadata = service.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    if metadata.get("mimeType") != "image/png" or metadata.get("name") != filename:
        raise RuntimeError(f"Unexpected Drive metadata for {filename}: {metadata}")
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, service.files().get_media(fileId=file_id))
    done = False
    while not done:
        _, done = downloader.next_chunk()
    raw = buffer.getvalue()
    if not raw.startswith(bytes([137, 80, 78, 71, 13, 10, 26, 10])):
        raise RuntimeError(f"Not a PNG: {filename}")
    with Image.open(io.BytesIO(raw)) as img:
        if img.size != (1080, 1350):
            raise RuntimeError(f"Unexpected dimensions for {filename}: {img.size}")
        img.verify()
    (out / filename).write_bytes(raw)
    jpeg_name = filename.removesuffix(".png") + ".jpg"
    with Image.open(io.BytesIO(raw)) as img:
        img.convert("RGB").save(out / jpeg_name, format="JPEG", quality=94, subsampling=0, optimize=True)
    with Image.open(out / jpeg_name) as jpg:
        if jpg.format != "JPEG" or jpg.size != (1080, 1350):
            raise RuntimeError(f"Invalid JPEG output: {jpeg_name}")
    print(f"Verified {filename}: {len(raw)} bytes; JPEG ready: {jpeg_name}")
print("All 7 files verified; Instagram publication is NOT performed.")
