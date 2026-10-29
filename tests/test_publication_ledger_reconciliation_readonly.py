import unittest
from datetime import datetime, timedelta, timezone
from scripts.presssport_ledger_reconciliation_readonly import inspect_ledger

NOW = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)

class Cursor:
    def __init__(self, rows): self.rows=rows; self.sql=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql): self.sql.append(sql)
    def fetchall(self): return self.rows
class DB:
    def __init__(self, rows): self.cur=Cursor(rows); self.closed=False
    def cursor(self): return self.cur
    def close(self): self.closed=True
    def commit(self): raise AssertionError("write transaction forbidden")

class LedgerDiagnosticTests(unittest.TestCase):
    def test_flags_uncertain_reconciliation_and_stale_publishing(self):
        rows=[
            ("publishing",False,NOW-timedelta(minutes=16),"old"),
            ("publishing",False,NOW-timedelta(minutes=1),"recent"),
            ("uncertain",True,NOW,"uncertain"),
            ("reserved",True,NOW,"flagged"),
            ("published",False,NOW,"done"),
        ]
        db=DB(rows)
        result=inspect_ledger(lambda url:db,"fixture",now=NOW)
        self.assertEqual(result["total"],5)
        self.assertEqual({x["publication_key"] for x in result["review"]},{"old","uncertain","flagged"})
        self.assertEqual(db.cur.sql[0],"BEGIN READ ONLY")
        self.assertEqual(db.cur.sql[-1],"ROLLBACK")
        self.assertTrue(db.closed)
    def test_empty_ledger(self):
        db=DB([])
        self.assertEqual(inspect_ledger(lambda url:db,"fixture",now=NOW)["review"],[])
    def test_missing_url(self):
        with self.assertRaises(ValueError):
            inspect_ledger(lambda _:self.fail("unexpected connect"),"",now=NOW)

if __name__=="__main__": unittest.main()
