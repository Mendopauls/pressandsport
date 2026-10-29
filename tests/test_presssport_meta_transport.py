import io
import json
import unittest
from urllib.error import URLError
from scripts.presssport_meta_transport import MetaGraphTransport

class Response:
    def __init__(self, data): self.data=data
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return json.dumps(self.data).encode()

class TransportTests(unittest.TestCase):
    def test_post_form_and_identifier(self):
        calls=[]
        def opener(req,timeout):
            calls.append((req.get_method(),req.full_url,req.data))
            return Response({"id":"12345"})
        meta=MetaGraphTransport("dummy",opener=opener)
        self.assertEqual(meta.post({"method":"POST","path":"/123/media","form":{"image_url":"https://example.org/a.jpg"}}),"12345")
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0],"POST")
        self.assertIn(b"access_token=dummy",calls[0][2])
    def test_get_status(self):
        meta=MetaGraphTransport("dummy",opener=lambda req,timeout:Response({"id":"123","status_code":"FINISHED"}))
        self.assertEqual(meta.status("123")["status_code"],"FINISHED")
    def test_network_error_no_retry(self):
        calls=[]
        def fail(req,timeout):
            calls.append(1)
            raise URLError("network")
        meta=MetaGraphTransport("dummy",opener=fail)
        with self.assertRaisesRegex(RuntimeError,"do not retry"):
            meta.post({"method":"POST","path":"/123/media","form":{}})
        self.assertEqual(len(calls),1)
    def test_reject_unexpected_path(self):
        meta=MetaGraphTransport("dummy",opener=lambda req,timeout:Response({"id":"123"}))
        with self.assertRaises(ValueError):
            meta.post({"method":"POST","path":"/123/other","form":{}})
    def test_no_live_entrypoint(self):
        import scripts.presssport_meta_transport as module
        self.assertFalse(hasattr(module,"main"))
if __name__=="__main__":unittest.main()
