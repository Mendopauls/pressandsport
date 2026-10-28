import hashlib
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from scripts.prepublish_guard import prepare_reservation
from scripts.check_publication_authorization import MANIFEST

class PrepublishGuardTests(unittest.TestCase):
    def setUp(self):
        self.data = json.dumps({"status":"approved","instagram_account_id":"123","image_urls":["https://example.com/a.jpg"]}).encode()
        self.auth = {
            "instagram_account_id":"123", "manifest_path":MANIFEST.as_posix(),
            "publish_authorized":True, "approved_by":"Paolo Savio",
            "manifest_sha256":hashlib.sha256(self.data).hexdigest(),
            "action":"publish_now", "authorized_at":"2026-10-28T12:00:00+00:00"
        }
        self.now = datetime(2026,10,28,12,15,tzinfo=timezone.utc)
        self.db = MagicMock()
    def call(self, auth=None, identity=True):
        return prepare_reservation(self.db,self.data,auth or self.auth,identity_verified=identity,now=self.now)
    def test_unverified_identity_blocks_db_write(self):
        with self.assertRaises(PermissionError):
            self.call(identity=False)
        self.db.cursor.assert_not_called()
    def test_missing_authorization_blocks_db_write(self):
        with self.assertRaises(PermissionError):
            self.call({**self.auth,"publish_authorized":False})
        self.db.cursor.assert_not_called()
    def test_wrong_manifest_digest_blocks_db_write(self):
        with self.assertRaises(PermissionError):
            self.call({**self.auth,"manifest_sha256":"0"*64})
        self.db.cursor.assert_not_called()
    def test_expired_authorization_blocks_db_write(self):
        with self.assertRaises(PermissionError):
            prepare_reservation(self.db,self.data,self.auth,identity_verified=True,now=datetime(2026,10,28,14,0,tzinfo=timezone.utc))
        self.db.cursor.assert_not_called()
    @patch("scripts.prepublish_guard.reserve_publication")
    def test_valid_gates_reach_reservation(self, reserve):
        reserve.return_value={"publication_key":"ok"}
        self.assertEqual(self.call(),{"publication_key":"ok"})
        reserve.assert_called_once_with(self.db,self.data)

if __name__ == "__main__":
    unittest.main()
