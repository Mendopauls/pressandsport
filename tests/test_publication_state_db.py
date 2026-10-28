import unittest
from scripts.publication_state_db import transition_reservation

class Cursor:
    def __init__(self, row=("key",)):
        self.row = row
        self.params = None
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params):
        assert "WHERE publication_key = %s AND attempt_id = %s AND state = %s" in sql
        self.params = params
    def fetchone(self): return self.row

class Connection:
    def __init__(self, row=("key",)):
        self.c = Cursor(row)
    def cursor(self): return self.c

class TestPublicationStateDB(unittest.TestCase):
    def test_reserved_to_publishing(self):
        conn = Connection()
        result = transition_reservation(conn, publication_key="key", attempt_id="attempt",
                                        from_state="reserved", to_state="publishing")
        self.assertEqual(result["state"], "publishing")
        self.assertEqual(conn.c.params[-1], "reserved")
    def test_conflict_blocks(self):
        with self.assertRaises(RuntimeError):
            transition_reservation(Connection(None), publication_key="key", attempt_id="attempt",
                                   from_state="reserved", to_state="publishing")
    def test_uncertain_requires_reconciliation(self):
        with self.assertRaises(ValueError):
            transition_reservation(Connection(), publication_key="key", attempt_id="attempt",
                                   from_state="publishing", to_state="uncertain")
    def test_published_requires_media_id(self):
        with self.assertRaises(ValueError):
            transition_reservation(Connection(), publication_key="key", attempt_id="attempt",
                                   from_state="publishing", to_state="published")
    def test_no_duplicate_publish(self):
        with self.assertRaises(ValueError):
            transition_reservation(Connection(), publication_key="key", attempt_id="attempt",
                                   from_state="published", to_state="publishing")
    def test_published_with_media_id(self):
        result = transition_reservation(Connection(), publication_key="key", attempt_id="attempt",
                                        from_state="publishing", to_state="published",
                                        meta_media_id="meta123")
        self.assertEqual(result["state"], "published")
    def test_uncertain_transition(self):
        result = transition_reservation(Connection(), publication_key="key", attempt_id="attempt",
                                        from_state="publishing", to_state="uncertain",
                                        reconciliation_required=True)
        self.assertEqual(result["state"], "uncertain")

if __name__ == "__main__":
    unittest.main()
