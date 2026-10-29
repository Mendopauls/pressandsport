import unittest
from datetime import datetime,timezone
from tests.test_publication_orchestrator import MANIFEST,AUTH,NOW,DB,Meta
from scripts.presssport_executor_boundary import execute_authorized

class Connection(DB):
    def __init__(self):
        super().__init__()
        self.closed=False
    def close(self):self.closed=True

class BoundaryTests(unittest.TestCase):
    def test_disabled_authorization_never_opens_connections(self):
        calls=[]
        def forbidden():
            calls.append("opened")
            raise AssertionError("unexpected external access")
        with self.assertRaises(PermissionError):
            execute_authorized(MANIFEST,dict(AUTH,publish_authorized=False),
                               verify=lambda _:forbidden(),connect=forbidden,make_meta=forbidden,now=NOW)
        self.assertEqual(calls,[])
    def test_identity_mismatch_never_opens_connections(self):
        calls=[]
        def forbidden():
            calls.append("opened")
            raise AssertionError("unexpected external access")
        with self.assertRaises(PermissionError):
            execute_authorized(MANIFEST,AUTH,
                verify=lambda _:{"verified":True,"account_id":"999"},
                connect=forbidden,make_meta=forbidden,now=NOW)
        self.assertEqual(calls,[])
    def test_success_closes_connection(self):
        db=Connection()
        result=execute_authorized(MANIFEST,AUTH,
            verify=lambda _:{"verified":True,"account_id":AUTH["instagram_account_id"]},
            connect=lambda:db,make_meta=lambda:Meta(db),now=NOW)
        self.assertEqual(result["state"],"published")
        self.assertTrue(db.closed)
    def test_failure_closes_connection(self):
        db=Connection()
        with self.assertRaises(Exception):
            execute_authorized(MANIFEST,AUTH,
                verify=lambda _:{"verified":True,"account_id":AUTH["instagram_account_id"]},
                connect=lambda:db,make_meta=lambda:Meta(db,fail=True),now=NOW)
        self.assertTrue(db.closed)
if __name__=="__main__":unittest.main()
