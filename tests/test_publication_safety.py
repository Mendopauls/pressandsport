"""Regression tests for PressSport read-only publication gates."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "publishing/presssport-2026-10-28.json").read_text(encoding="utf-8"))
AUTH = json.loads((ROOT / "publishing/presssport-2026-10-28-authorization.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(ROOT / "scripts"))
from meta_publication_readiness import check as readiness_check

class PublicationSafetyTests(unittest.TestCase):
    def test_approved_carousel_is_editorially_ready(self):
        self.assertEqual(readiness_check(MANIFEST), [])

    def test_caption_missing_blocks(self):
        data = copy.deepcopy(MANIFEST)
        data["caption"] = ""
        self.assertTrue(readiness_check(data))

    def test_unapproved_manifest_blocks(self):
        data = copy.deepcopy(MANIFEST)
        data["status"] = "draft"
        self.assertTrue(readiness_check(data))

    def test_wrong_account_blocks(self):
        data = copy.deepcopy(MANIFEST)
        data["instagram_account_id"] = "wrong"
        self.assertTrue(readiness_check(data))

    def test_changed_media_blocks(self):
        data = copy.deepcopy(MANIFEST)
        data["image_urls"].reverse()
        self.assertTrue(readiness_check(data))

    def test_authorization_defaults_to_denied(self):
        self.assertIs(AUTH["publish_authorized"], False)
        self.assertIsNone(AUTH["authorized_at"])
        self.assertIsNone(AUTH["action"])

    def test_duplicate_ledger_blocks_published_entry(self):
        with TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            ledger = Path(tmp) / "ledger.json"
            manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
            ledger.write_text(json.dumps([{
                "instagram_account_id": MANIFEST["instagram_account_id"],
                "image_urls": MANIFEST["image_urls"],
                "status": "published"
            }]), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/check_publication_ledger.py"),
                 "--manifest", str(manifest), "--ledger", str(ledger)],
                capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("BLOCKED", result.stdout)

    def test_ledger_allows_new_media_only(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_publication_ledger.py")],
            cwd=ROOT, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
