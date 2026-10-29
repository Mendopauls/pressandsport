import unittest
from scripts.presssport_transaction_rollback_probe import probe_transactions

class UniqueViolation(Exception):
    sqlstate = "23505"

class Cursor:
    def __init__(self): self.commands=[]; self.fetch=[("reserved",),("publishing",),None]; self.inserts=0
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql,params=None):
        self.commands.append(sql)
        if sql.startswith("INSERT"):
            self.inserts+=1
            if self.inserts==2: raise UniqueViolation("duplicate")
    def fetchone(self): return self.fetch.pop(0)
class DB:
    def __init__(self): self.cur=Cursor(); self.rolled_back=False; self.closed=False
    def cursor(self): return self.cur
    def rollback(self): self.rolled_back=True
    def close(self): self.closed=True
    def commit(self): raise AssertionError("commit is forbidden")

class TransactionProbeTests(unittest.TestCase):
    def test_duplicate_cas_stale_and_rollback(self):
        db=DB()
        result=probe_transactions(lambda url:db,"fixture")
        self.assertTrue(result["duplicate_rejected"])
        self.assertTrue(result["cas_transition"])
        self.assertTrue(result["stale_transition_rejected"])
        self.assertFalse(result["committed"])
        self.assertTrue(db.rolled_back)
        self.assertTrue(db.closed)
        self.assertTrue(any("ROLLBACK TO SAVEPOINT" in sql for sql in db.cur.commands))
    def test_missing_url_never_connects(self):
        with self.assertRaises(ValueError):
            probe_transactions(lambda url:self.fail("unexpected connect"),"")

if __name__=="__main__": unittest.main()
