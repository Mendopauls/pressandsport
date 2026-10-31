import unittest
from datetime import datetime, timezone, timedelta
from scripts.presssport_multichannel_queue import insert_draft, move_state

class Cursor:
    def __init__(self, result): self.result = result; self.statements = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, args): self.statements.append((sql, args))
    def fetchone(self): return self.result

class Connection:
    def __init__(self, result): self.cur = Cursor(result)
    def cursor(self): return self.cur

class QueueUnitTests(unittest.TestCase):
    def test_insert_draft_never_authorizes(self):
        c = Connection(("test-post-001", "draft"))
        result = insert_draft(
            c, post_key="test-post-001", kind="instagram_image",
            caption="Test", image_urls=["https://pressandsport.it/asset.jpg"],
            account_id="17841425937268080")
        self.assertFalse(result["publication_authorized"])
        self.assertIn("INSERT INTO", c.cur.statements[0][0])

    def test_approval_requires_named_operator(self):
        c = Connection(("test-post-001", "approved"))
        with self.assertRaises(PermissionError):
            move_state(c, post_key="test-post-001", from_state="ready_for_review",
                       to_state="approved", operator="Unknown")
        self.assertEqual(c.cur.statements, [])

    def test_planned_must_be_future(self):
        now = datetime(2026, 10, 31, tzinfo=timezone.utc)
        c = Connection(("test-post-001", "planned"))
        with self.assertRaises(ValueError):
            move_state(c, post_key="test-post-001", from_state="approved",
                       to_state="planned", operator="Paolo Savio",
                       planned_at=now - timedelta(seconds=1), now=now)
        self.assertEqual(c.cur.statements, [])

    def test_valid_review_transition_not_a_release(self):
        c = Connection(("test-post-001", "ready_for_review"))
        result = move_state(c, post_key="test-post-001", from_state="draft",
                            to_state="ready_for_review", operator="Paolo Savio")
        self.assertFalse(result["publication_authorized"])

    def test_invalid_transition_rejected(self):
        c = Connection(("test-post-001", "planned"))
        with self.assertRaises(ValueError):
            move_state(c, post_key="test-post-001", from_state="draft",
                       to_state="planned", operator="Paolo Savio")
        self.assertEqual(c.cur.statements, [])

if __name__ == "__main__":
    unittest.main()
