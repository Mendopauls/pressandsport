import io
import unittest
from urllib.error import URLError
from scripts.meta_graph_transport import post_graph, MetaOutcomeUncertain

class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.request = {"method": "POST", "path": "/123/media",
                        "form": {"image_url": "https://example.com/photo.jpg"}}
    def test_success(self):
        calls = []
        def opener(request, timeout):
            calls.append((request.full_url, request.data, timeout))
            return Response(b'{"id":"987"}')
        self.assertEqual(post_graph(self.request, access_token="fake-token", opener=opener), "987")
        self.assertEqual(len(calls), 1)
        self.assertIn(b"access_token=fake-token", calls[0][1])
    def test_network_failure_no_retry(self):
        calls = []
        def opener(request, timeout):
            calls.append(True)
            raise URLError("network down")
        with self.assertRaises(MetaOutcomeUncertain):
            post_graph(self.request, access_token="fake-token", opener=opener)
        self.assertEqual(len(calls), 1)
    def test_invalid_json_uncertain(self):
        with self.assertRaises(MetaOutcomeUncertain):
            post_graph(self.request, access_token="fake-token",
                       opener=lambda req, timeout: Response(b"invalid"))
    def test_missing_id_uncertain(self):
        with self.assertRaises(MetaOutcomeUncertain):
            post_graph(self.request, access_token="fake-token",
                       opener=lambda req, timeout: Response(b'{"error":"failure"}'))
    def test_token_required(self):
        with self.assertRaises(ValueError):
            post_graph(self.request, access_token="")
    def test_path_validation(self):
        with self.assertRaises(ValueError):
            post_graph({"method":"POST","path":"https://evil.example","form":{"a":"b"}},
                       access_token="fake-token")

if __name__ == "__main__":
    unittest.main()
