"""Offline transactional ledger lifecycle checks. No live database or Meta access."""
import unittest
from scripts.publication_state_db import transition_reservation

class MemoryCursor:
    def __init__(self, db):
        self.db = db
        self.result = None
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params):
        new_state, media_id, reconcile, key, attempt, old_state = params
        row = self.db.row
        if row["key"] != key or row["attempt"] != attempt or row["state"] != old_state:
            self.result = None
            return
        self.db.pending = dict(row, state=new_state, media_id=media_id, reconcile=reconcile)
        self.result = (key,)
    def fetchone(self): return self.result

class MemoryDB:
    def __init__(self):
        self.row = dict(key="key", attempt="attempt", state="reserved",
                        media_id=None, reconcile=False)
        self.pending = None
        self.commits = 0
    def cursor(self): return MemoryCursor(self)
    def commit(self):
        if self.pending is not None:
            self.row = self.pending
            self.pending = None
        self.commits += 1
    def rollback(self):
        self.pending = None

def change(db, old, new, **kwargs):
    transition_reservation(db, publication_key="key", attempt_id="attempt",
                           from_state=old, to_state=new, **kwargs)
    db.commit()

class TransactionLifecycleTests(unittest.TestCase):
    def test_committed_publishing_and_published(self):
        db = MemoryDB()
        change(db, "reserved", "publishing")
        self.assertEqual(db.row["state"], "publishing")
        change(db, "publishing", "published", meta_media_id="12345")
        self.assertEqual(db.row["state"], "published")
        self.assertEqual(db.row["media_id"], "12345")
        self.assertEqual(db.commits, 2)
    def test_uncertain_requires_reconciliation_and_blocks_reuse(self):
        db = MemoryDB()
        change(db, "reserved", "publishing")
        change(db, "publishing", "uncertain", reconciliation_required=True)
        self.assertTrue(db.row["reconcile"])
        with self.assertRaises(ValueError):
            change(db, "uncertain", "publishing")
        self.assertEqual(db.row["state"], "uncertain")
    def test_conflicting_attempt_is_rejected(self):
        db = MemoryDB()
        with self.assertRaises(RuntimeError):
            transition_reservation(db, publication_key="key", attempt_id="other",
                                   from_state="reserved", to_state="publishing")
        self.assertIsNone(db.pending)
    def test_uncommitted_change_is_not_visible(self):
        db = MemoryDB()
        transition_reservation(db, publication_key="key", attempt_id="attempt",
                               from_state="reserved", to_state="publishing")
        self.assertEqual(db.row["state"], "reserved")
        db.rollback()
        self.assertEqual(db.row["state"], "reserved")
    def test_stale_state_cannot_overwrite(self):
        db = MemoryDB()
        change(db, "reserved", "publishing")
        with self.assertRaises(RuntimeError):
            change(db, "reserved", "publishing")
        self.assertEqual(db.row["state"], "publishing")
    def test_published_is_terminal(self):
        db = MemoryDB()
        change(db, "reserved", "publishing")
        change(db, "publishing", "published", meta_media_id="12345")
        with self.assertRaises(ValueError):
            change(db, "published", "publishing")
        self.assertEqual(db.row["state"], "published")

if __name__ == "__main__":
    unittest.main()
