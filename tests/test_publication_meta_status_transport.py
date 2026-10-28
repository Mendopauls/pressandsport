import unittest
from urllib.error import URLError
from scripts.meta_graph_status_transport import get_container_status, MetaStatusUnavailable

class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload

class MetaStatusTransportTests(unittest.TestCase):
    def test_ready(self):
        calls = []
        def opener(request, timeout):
            calls.append(request)
            return Response(b'{"id":"123","status_code":"FINISHED"}')
        result = get_container_status("123", access_token="test-token", opener=opener)
        self.assertEqual(result["classification"], "ready")
        self.assertEqual(calls[0].get_method(), "GET")
        self.assertIn("fields=id%2Cstatus_code", calls[0].full_url)
    def test_pending(self):
        result = get_container_status("123", access_token="test", opener=lambda r,timeout: Response(b'{"id":"123","status_code":"IN_PROGRESS"}'))
        self.assertEqual(result["classification"], "pending")
    def test_mismatch_fails_closed(self):
        with self.assertRaises(MetaStatusUnavailable):
            get_container_status("123", access_token="test", opener=lambda r,timeout: Response(b'{"id":"456","status_code":"FINISHED"}'))
    def test_network_fails_closed(self):
        def opener(request, timeout): raise URLError("offline")
        with self.assertRaises(MetaStatusUnavailable):
            get_container_status("123", access_token="test", opener=opener)
    def test_missing_token(self):
        with self.assertRaises(ValueError):
            get_container_status("123", access_token="")
    def test_invalid_version(self):
        with self.assertRaises(ValueError):
            get_container_status("123", access_token="test", api_version="v24.0/evil")

if __name__ == "__main__":
    unittest.main()
