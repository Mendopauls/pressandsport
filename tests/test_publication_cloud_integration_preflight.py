import unittest
from scripts.presssport_cloud_integration_preflight import verify_cloud_readiness

class Cursor:
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql): pass
    def fetchone(self): return (0,)
class Connection:
    def __init__(self): self.closed=False
    def cursor(self): return Cursor()
    def close(self): self.closed=True

class CloudPreflightTests(unittest.TestCase):
    def test_closed_authorization_and_readonly_db(self):
        db=Connection()
        result=verify_cloud_readiness(lambda url:db,"fixture",
            manifest_bytes=b'{"status":"approved"}',
            authorization={"publish_authorized":False})
        self.assertTrue(result["authorization_blocked"])
        self.assertFalse(result["publication_performed"])
        self.assertTrue(db.closed)
    def test_open_authorization_fails_before_connect(self):
        with self.assertRaises(PermissionError):
            verify_cloud_readiness(lambda url:self.fail("must not connect"),"fixture",
                manifest_bytes=b'{"status":"approved"}',
                authorization={"publish_authorized":True})

if __name__=="__main__": unittest.main()
