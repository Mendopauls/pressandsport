import json
import unittest

from scripts.presssport_media_preflight import verify_media

JPEG = bytes.fromhex("ffd8ff") + b"image" + bytes.fromhex("ffd9")

class Response:
    status = 200
    headers = {"content-type": "image/jpeg"}
    def __init__(self, url, data=JPEG):
        self.url = url
        self.data = data
    def geturl(self): return self.url
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.data[:n]

def manifest(urls):
    return json.dumps({"instagram_account_id": "17841425937268080",
        "status": "approved", "caption": "Test caption", "image_urls": urls}).encode()

URLS = ["https://pressandsport.it/media/one.jpg", "https://pressandsport.it/media/two.jpg"]

class MediaTests(unittest.TestCase):
    def test_two_valid_jpegs(self):
        calls=[]
        def opener(req, timeout):
            calls.append(req.full_url)
            return Response(req.full_url)
        report=verify_media(manifest(URLS), opener=opener)
        self.assertTrue(report["all_reachable"])
        self.assertEqual(report["image_count"], 2)
        self.assertEqual(len(calls), 2)
        self.assertFalse(report["publication_performed"])
    def test_duplicate_rejected_before_network(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify_media(manifest([URLS[0], URLS[0]]), opener=lambda *a,**kw: self.fail("network"))
    def test_wrong_host_rejected(self):
        with self.assertRaisesRegex(ValueError,"unexpected public media host"):
            verify_media(manifest(["https://example.org/one.jpg", URLS[1]]), opener=lambda *a,**kw:self.fail("network"))
    def test_bad_mime_fails(self):
        def bad(req, timeout):
            response=Response(req.full_url)
            response.headers={"content-type":"text/html"}
            return response
        with self.assertRaisesRegex(RuntimeError,"slide 1"):
            verify_media(manifest(URLS), opener=bad)
    def test_non_jpeg_fails(self):
        with self.assertRaisesRegex(ValueError,"invalid or excessive"):
            verify_media(manifest(URLS), opener=lambda req,timeout: Response(req.full_url,b"not a jpeg"))
    def test_redirected_host_fails(self):
        with self.assertRaisesRegex(RuntimeError,"slide 1"):
            verify_media(manifest(URLS), opener=lambda req,timeout: Response("https://example.org/redirect.jpg"))
    def test_byte_limit_fails(self):
        with self.assertRaisesRegex(ValueError,"invalid or excessive"):
            verify_media(manifest(URLS), opener=lambda req,timeout: Response(req.full_url,JPEG*3),max_bytes=10)

if __name__=="__main__":
    unittest.main()
