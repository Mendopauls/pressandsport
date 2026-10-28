import unittest
from scripts.meta_container_status import (
    ContainerStatusError, status_request, classify_container_status, require_all_ready,
)

class ContainerStatusTests(unittest.TestCase):
    def test_request(self):
        self.assertEqual(status_request("123")["params"], {"fields": "id,status_code"})
    def test_ready(self):
        self.assertEqual(classify_container_status("123", {"id":"123","status_code":"FINISHED"}), "ready")
    def test_pending(self):
        self.assertEqual(classify_container_status("123", {"id":"123","status_code":"IN_PROGRESS"}), "pending")
    def test_error(self):
        self.assertEqual(classify_container_status("123", {"id":"123","status_code":"ERROR"}), "failed")
    def test_mismatch(self):
        with self.assertRaises(ContainerStatusError):
            classify_container_status("123", {"id":"456","status_code":"FINISHED"})
    def test_unknown_status(self):
        with self.assertRaises(ContainerStatusError):
            classify_container_status("123", {"id":"123","status_code":"UNEXPECTED"})
    def test_all_ready(self):
        self.assertTrue(require_all_ready(["1","2"], [{"id":"1","status_code":"FINISHED"},{"id":"2","status_code":"FINISHED"}]))
    def test_pending_blocks(self):
        with self.assertRaises(ContainerStatusError):
            require_all_ready(["1","2"], [{"id":"1","status_code":"FINISHED"},{"id":"2","status_code":"IN_PROGRESS"}])
    def test_duplicates_block(self):
        with self.assertRaises(ContainerStatusError):
            require_all_ready(["1","1"], [{"id":"1","status_code":"FINISHED"}]*2)

if __name__ == "__main__":
    unittest.main()
