import json
import unittest
from pathlib import Path
from scripts.meta_carousel_plan import plan_carousel

MANIFEST = Path("publishing/presssport-2026-10-28.json")

class MetaCarouselPlanTests(unittest.TestCase):
    def test_approved_manifest(self):
        plan = plan_carousel(MANIFEST.read_bytes())
        self.assertEqual(len(plan["children"]), 7)
        self.assertEqual(plan["parent"]["media_type"], "CAROUSEL")
        self.assertTrue(plan["publish"]["requires_explicit_authorization"])
        self.assertTrue(all(x["is_carousel_item"] == "true" for x in plan["children"]))
    def test_unapproved_blocked(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["status"] = "draft"
        with self.assertRaises(ValueError):
            plan_carousel(json.dumps(manifest).encode())
    def test_insecure_url_blocked(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["image_urls"][0] = "http://example.com/image.jpg"
        with self.assertRaises(ValueError):
            plan_carousel(json.dumps(manifest).encode())
    def test_empty_caption_blocked(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["caption"] = ""
        with self.assertRaises(ValueError):
            plan_carousel(json.dumps(manifest).encode())
    def test_too_many_images_blocked(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["image_urls"] *= 2
        with self.assertRaises(ValueError):
            plan_carousel(json.dumps(manifest).encode())

if __name__ == "__main__":
    unittest.main()
