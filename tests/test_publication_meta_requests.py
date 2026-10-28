import unittest
from pathlib import Path
from scripts.meta_carousel_requests import child_requests, parent_request, publish_request

MANIFEST = Path("publishing/presssport-2026-10-28.json").read_bytes()

class CarouselRequestsTests(unittest.TestCase):
    def test_seven_children(self):
        requests = child_requests(MANIFEST)
        self.assertEqual(len(requests), 7)
        self.assertTrue(all(r["path"].endswith("/media") for r in requests))
        self.assertTrue(all(r["form"]["is_carousel_item"] == "true" for r in requests))
    def test_parent_request(self):
        request = parent_request(MANIFEST, [str(x) for x in range(100,107)])
        self.assertEqual(request["form"]["media_type"], "CAROUSEL")
        self.assertEqual(request["form"]["children"], "100,101,102,103,104,105,106")
    def test_missing_child_blocked(self):
        with self.assertRaises(ValueError):
            parent_request(MANIFEST, ["100"])
    def test_duplicate_child_blocked(self):
        with self.assertRaises(ValueError):
            parent_request(MANIFEST, ["100"] * 7)
    def test_publish_request(self):
        request = publish_request(MANIFEST, "123456")
        self.assertTrue(request["path"].endswith("/media_publish"))
        self.assertEqual(request["form"], {"creation_id": "123456"})
    def test_bad_parent_id_blocked(self):
        with self.assertRaises(ValueError):
            publish_request(MANIFEST, "not-an-id")

if __name__ == "__main__":
    unittest.main()
