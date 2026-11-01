import unittest
from scripts.presssport_multichannel_manifest import validate_manifest, verify_release

IG = "17841425937268080"
LI = "146625659"
URL = "https://pressandsport.it/assets/test.jpg"

class MultichannelManifestTests(unittest.TestCase):
    def make(self, kind="instagram_image", count=1, account=IG, caption="Test"):
        return validate_manifest(post_key="test-post-001", kind=kind, caption=caption,
                                 image_urls=[f"https://pressandsport.it/assets/{i}.jpg" for i in range(count)],
                                 account_id=account)

    def test_single_image(self):
        self.assertFalse(self.make()["publication_authorized"])

    def test_carousel(self):
        self.assertEqual(len(self.make(kind="instagram_carousel", count=7)["image_urls"]), 7)

    def test_story_without_caption(self):
        self.assertEqual(self.make(kind="instagram_story", caption="")["caption"], "")

    def test_linkedin_account(self):
        self.assertEqual(self.make(kind="linkedin_image", account=LI)["account_id"], LI)

    def test_wrong_account_rejected(self):
        with self.assertRaises(ValueError):
            self.make(kind="linkedin_image", account=IG)

    def test_carousel_needs_multiple_images(self):
        with self.assertRaises(ValueError):
            self.make(kind="instagram_carousel")

    def test_query_url_rejected(self):
        with self.assertRaises(ValueError):
            validate_manifest(post_key="test-post-001", kind="instagram_image",
                              caption="Test", image_urls=[URL + "?token=1"], account_id=IG)

    def test_release_requires_explicit_match(self):
        manifest = self.make()
        digest = manifest["content_sha256"]
        self.assertFalse(verify_release(manifest, approved_digest=digest,
                                        approved_account=IG, explicit_authorization=False))
        self.assertFalse(verify_release(manifest, approved_digest="0"*64,
                                        approved_account=IG, explicit_authorization=True))
        self.assertFalse(verify_release(manifest, approved_digest=digest,
                                        approved_account=LI, explicit_authorization=True))
        self.assertTrue(verify_release(manifest, approved_digest=digest,
                                       approved_account=IG, explicit_authorization=True))

if __name__ == "__main__":
    unittest.main()
