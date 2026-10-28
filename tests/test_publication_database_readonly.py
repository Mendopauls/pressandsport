import unittest
from scripts.presssport_database_readonly import inspect_publication_ledger

class Cursor:
    def __init__(self, count): self.count=count; self.statements=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql): self.statements.append(sql)
    def fetchone(self): return (self.count,)
class Connection:
    def __init__(self,count): self.c=Cursor(count); self.closed=False
    def cursor(self): return self.c
    def close(self): self.closed=True
class DatabaseReadOnlyTests(unittest.TestCase):
    def test_readonly_transaction_and_close(self):
        conn=Connection(0)
        result=inspect_publication_ledger(lambda url: conn,"fixture")
        self.assertTrue(result["ledger_accessible"])
        self.assertEqual(result["reservation_count"],0)
        self.assertEqual(conn.c.statements,[
            "BEGIN READ ONLY",
            "SELECT count(*) FROM presssport_internal.publication_reservations",
            "ROLLBACK"])
        self.assertTrue(conn.closed)
    def test_missing_database_url(self):
        with self.assertRaises(ValueError):
            inspect_publication_ledger(lambda url: self.fail("unexpected connect"),"")
    def test_invalid_result_closes_connection(self):
        conn=Connection(None)
        with self.assertRaises(RuntimeError):
            inspect_publication_ledger(lambda url:conn,"fixture")
        self.assertTrue(conn.closed)

if __name__=="__main__": unittest.main()
