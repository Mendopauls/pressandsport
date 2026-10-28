import io
import json
import unittest
from urllib.request import Request
from scripts.meta_identity_readonly import verify_identity

MANIFEST = json.dumps({"instagram_account_id": "17841425937268080"}).encode()

class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode()

class MetaIdentityTests(unittest.TestCase):
    def test_correct_identity(self):
        calls = []
        def opener(req, timeout):
            self.assertIsInstance(req, Request)
            self.assertEqual(req.get_method(), "GET")
            calls.append(req)
            return Response({"id": "17841425937268080", "username": "pressandsport"})
        self.assertTrue(verify_identity(MANIFEST, "test-token", opener=opener)["verified"])
        self.assertEqual(len(calls), 1)
    def test_wrong_id(self):
        with self.assertRaises(RuntimeError):
            verify_identity(MANIFEST, "test-token", opener=lambda req, timeout: Response(
                {"id": "123", "username": "pressandsport"}))
    def test_wrong_username(self):
        with self.assertRaises(RuntimeError):
            verify_identity(MANIFEST, "test-token", opener=lambda req, timeout: Response(
                {"id": "17841425937268080", "username": "other"}))
    def test_missing_token_prevents_network(self):
        with self.assertRaises(ValueError):
            verify_identity(MANIFEST, "", opener=lambda req, timeout: self.fail("network accessed"))
    def test_invalid_manifest_prevents_network(self):
        with self.assertRaises(ValueError):
            verify_identity(b'{"instagram_account_id":"not-valid"}', "token",
                            opener=lambda req, timeout: self.fail("network accessed"))

if __name__ == "__main__":
    unittest.main()
