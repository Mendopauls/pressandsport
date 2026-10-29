import hashlib
import json
import unittest
from pathlib import Path
from scripts.presssport_cloud_publisher import run_dry_run

MANIFEST=Path("publishing/presssport-2026-10-28.json").read_bytes()
AUTH=json.loads(Path("publishing/presssport-2026-10-28-authorization.json").read_text())

class Cursor:
    def __init__(self): self.query=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql): self.query.append(sql)
    def fetchone(self): return (0,)
    def fetchall(self): return []
class DB:
    def __init__(self): self.cur=Cursor(); self.closed=False
    def cursor(self): return self.cur
    def close(self): self.closed=True
    def commit(self): raise AssertionError("commit forbidden")

class CloudDryRunTests(unittest.TestCase):
    def test_integrated_read_only_dry_run(self):
        connections=[]
        def connect(url):
            db=DB(); connections.append(db); return db
        result=run_dry_run(
            connect,"fixture",manifest_bytes=MANIFEST,authorization=AUTH,token="fake",
            verify=lambda raw,token:{"verified":True,"account_id":json.loads(raw)["instagram_account_id"]})
        self.assertEqual(result["mode"],"dry_run")
        self.assertFalse(result["published"])
        self.assertEqual(result["meta_post_calls"],0)
        self.assertEqual(len(connections),2)
        self.assertTrue(all(db.closed for db in connections))
        self.assertTrue(all(db.cur.query[0]=="BEGIN READ ONLY" for db in connections))
    def test_authorized_manifest_blocked_before_any_network(self):
        with self.assertRaises(PermissionError):
            run_dry_run(lambda _:self.fail("database called"),"fixture",
                        manifest_bytes=MANIFEST,authorization=dict(AUTH,publish_authorized=True),
                        token="fake",verify=lambda *_:self.fail("Meta called"))
    def test_identity_mismatch_blocks_db(self):
        with self.assertRaises(RuntimeError):
            run_dry_run(lambda _:self.fail("database called"),"fixture",
                        manifest_bytes=MANIFEST,authorization=AUTH,token="fake",
                        verify=lambda *_:{"verified":True,"account_id":"wrong"})

if __name__=="__main__": unittest.main()
