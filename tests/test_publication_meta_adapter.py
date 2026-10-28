import unittest
from scripts.presssport_meta_adapter import MetaAdapter

class MetaAdapterTests(unittest.TestCase):
    def test_status_ready(self):
        adapter=MetaAdapter("fixture-token",get=lambda cid,**kw: {"container_id":cid,"classification":"ready"})
        self.assertEqual(adapter.status("123"),{"id":"123","status_code":"FINISHED"})
    def test_status_pending(self):
        adapter=MetaAdapter("fixture-token",get=lambda cid,**kw: {"container_id":cid,"classification":"pending"})
        self.assertEqual(adapter.status("123")["status_code"],"IN_PROGRESS")
    def test_status_mismatch(self):
        adapter=MetaAdapter("fixture-token",get=lambda cid,**kw: {"container_id":"999","classification":"ready"})
        with self.assertRaises(RuntimeError): adapter.status("123")
    def test_unknown_status(self):
        adapter=MetaAdapter("fixture-token",get=lambda cid,**kw: {"container_id":cid,"classification":"unknown"})
        with self.assertRaises(RuntimeError): adapter.status("123")
    def test_missing_token(self):
        with self.assertRaises(ValueError): MetaAdapter("")

if __name__=="__main__": unittest.main()
