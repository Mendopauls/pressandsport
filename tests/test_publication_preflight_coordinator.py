import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from scripts.presssport_publisher_preflight import preflight
from scripts.check_publication_authorization import MANIFEST

class PublisherPreflightTests(unittest.TestCase):
    def setUp(self):
        self.manifest = Path(MANIFEST).read_bytes()
        self.auth = json.loads(Path("publishing/presssport-2026-10-28-authorization.json").read_text())
        self.now = datetime(2026, 10, 28, 12, 10, tzinfo=timezone.utc)
    def test_current_authorization_blocks(self):
        result = preflight(self.manifest, self.auth, identity_verified=True, now=self.now)
        self.assertFalse(result["ready"])
        self.assertFalse(result["publication_performed"])
    def test_unverified_identity_blocks(self):
        result = preflight(self.manifest, self.auth, identity_verified=False, now=self.now)
        self.assertFalse(result["ready"])
        self.assertTrue(any("identity" in x for x in result["blockers"]))
    def test_valid_authorization_only_builds_plan(self):
        auth = dict(self.auth, publish_authorized=True, approved_by="Paolo Savio",
                    manifest_sha256=hashlib.sha256(self.manifest).hexdigest(),
                    action="publish_now", authorized_at="2026-10-28T12:00:00+00:00")
        result = preflight(self.manifest, auth, identity_verified=True, now=self.now)
        self.assertTrue(result["ready"])
        self.assertEqual(result["image_count"], 7)
        self.assertFalse(result["publication_performed"])
    def test_expired_authorization_blocks(self):
        auth = dict(self.auth, publish_authorized=True, approved_by="Paolo Savio",
                    manifest_sha256=hashlib.sha256(self.manifest).hexdigest(),
                    action="publish_now", authorized_at="2026-10-28T08:00:00+00:00")
        self.assertFalse(preflight(self.manifest, auth, identity_verified=True, now=self.now)["ready"])

if __name__ == "__main__":
    unittest.main()
