import unittest
from scripts.presssport_transaction_schema_readonly import (
    REQUIRED, inspect_transaction_schema,
)

class Cursor:
    def __init__(self, names): self.names=names; self.statements=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql): self.statements.append(sql)
    def fetchall(self): return [(name,) for name in self.names]

class Connection:
    def __init__(self,names): self.c=Cursor(names); self.closed=False
    def cursor(self): return self.c
    def close(self): self.closed=True

class SchemaReadOnlyTests(unittest.TestCase):
    def test_complete_schema(self):
        db=Connection(REQUIRED)
        result=inspect_transaction_schema(lambda url:db,"fixture")
        self.assertTrue(result["schema_valid"])
        self.assertFalse(result["database_writes"])
        self.assertEqual(db.c.statements[0],"BEGIN READ ONLY")
        self.assertEqual(db.c.statements[-1],"ROLLBACK")
        self.assertTrue(db.closed)
    def test_missing_column_fails_closed(self):
        db=Connection(REQUIRED-{"attempt_id"})
        with self.assertRaisesRegex(RuntimeError,"attempt_id"):
            inspect_transaction_schema(lambda url:db,"fixture")
        self.assertTrue(db.closed)
    def test_missing_connection_string(self):
        with self.assertRaises(ValueError):
            inspect_transaction_schema(lambda url:self.fail("unexpected connection"),"")

if __name__=="__main__": unittest.main()
