"""Tests for immutable manifest publication authorization."""
import hashlib
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_publication_authorization import MANIFEST, validate

class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = (ROOT / MANIFEST).read_bytes()
        self.now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        self.auth = {
            "instagram_account_id": "17841425937268080",
            "manifest_path": MANIFEST.as_posix(),
            "publish_authorized": True,
            "approved_by": "Paolo Savio",
            "manifest_sha256": hashlib.sha256(self.manifest).hexdigest(),
            "authorized_at": self.now.isoformat(),
            "action": "publish_now",
            "scheduled_at": None,
        }

    def test_valid_record(self):
        self.assertEqual(validate(self.manifest, self.auth, self.now), [])

    def test_default_denied(self):
        self.auth["publish_authorized"] = False
        self.assertTrue(validate(self.manifest, self.auth, self.now))

    def test_changed_manifest_denied(self):
        self.assertTrue(validate(self.manifest + b" ", self.auth, self.now))

    def test_missing_digest_denied(self):
        self.auth.pop("manifest_sha256")
        self.assertTrue(validate(self.manifest, self.auth, self.now))

    def test_expired_approval_denied(self):
        self.auth["authorized_at"] = (self.now - timedelta(hours=2)).isoformat()
        self.assertTrue(validate(self.manifest, self.auth, self.now))

    def test_future_dated_approval_denied(self):
        self.auth["authorized_at"] = (self.now + timedelta(minutes=10)).isoformat()
        self.assertTrue(validate(self.manifest, self.auth, self.now))

    def test_invalid_schedule_denied(self):
        self.auth["action"] = "schedule"
        self.auth["scheduled_at"] = (self.now - timedelta(minutes=1)).isoformat()
        self.assertTrue(validate(self.manifest, self.auth, self.now))

if __name__ == "__main__":
    unittest.main()
