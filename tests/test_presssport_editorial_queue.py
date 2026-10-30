import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts.presssport_editorial_queue import (
    normalized_post, enqueue_draft, transition_editorial, inspect_due_plans
)

URLS = ["https://pressandsport.it/img/one.jpg", "https://pressandsport.it/img/two.jpg"]
NOW = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
POST = {"post_key": "presssport-post-2026-11-02", "caption": "Comunicazione sportiva",
        "image_urls": URLS}

class Cursor:
    def __init__(self, db): self.db = db
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, args):
        self.db.calls.append((sql, args))
    def fetchone(self): return self.db.next_row
    def fetchall(self): return self.db.next_rows
class DB:
    def __init__(self, next_row=None, next_rows=None):
        self.calls = []; self.next_row = next_row; self.next_rows = next_rows or []
    def cursor(self): return Cursor(self)

class QueueTests(unittest.TestCase):
    def test_valid_post_and_stable_hash(self):
        a = normalized_post(**POST)
        b = normalized_post(**POST)
        self.assertEqual(a["content_sha256"], b["content_sha256"])
        self.assertEqual(len(a["content_sha256"]), 64)

    def test_reject_untrusted_host_and_non_jpeg(self):
        for url in ("http://pressandsport.it/a.jpg",
                    "https://evil.test/a.jpg",
                    "https://pressandsport.it/a.png",
                    "https://pressandsport.it/a.jpg?token=hidden",
                    "https://pressandsport.it@evil.test/a.jpg"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalized_post("valid-post", "caption", [url, URLS[0]])

    def test_reject_duplicate_and_too_many_images(self):
        for urls in ([URLS[0], URLS[0]], URLS[:1], URLS * 6):
            with self.assertRaises(ValueError):
                normalized_post("valid-post", "caption", urls)

    def test_reject_wrong_account_and_invalid_caption(self):
        with self.assertRaises(ValueError):
            normalized_post("valid-post", "caption", URLS, account="123")
        with self.assertRaises(ValueError):
            normalized_post("valid-post", "  ", URLS)

    def test_create_draft_only(self):
        db = DB(next_row=(POST["post_key"], "draft"))
        result = enqueue_draft(db, POST)
        self.assertFalse(result["publication_authorized"])
        self.assertIn("INSERT INTO presssport_internal.editorial_queue", db.calls[0][0])
        self.assertNotIn("publication_reservations", db.calls[0][0])

    def test_editorial_transition_and_approval(self):
        db = DB(next_row=(POST["post_key"], "approved"))
        result = transition_editorial(db, post_key=POST["post_key"],
           from_state="ready_for_review",to_state="approved",approved_by="Paolo Savio")
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(result["editorial_state"], "approved")

    def test_reject_editorial_approval_without_named_approver(self):
        db=DB()
        with self.assertRaises(PermissionError):
            transition_editorial(db,post_key=POST["post_key"],from_state="ready_for_review",
                                to_state="approved",approved_by="other person")
        self.assertFalse(db.calls)

    def test_planning_never_authorizes_publication(self):
        db = DB(next_row=(POST["post_key"], "planned"))
        result=transition_editorial(db,post_key=POST["post_key"],from_state="approved",
              to_state="planned",planned_at=NOW+timedelta(days=1),now=NOW)
        self.assertFalse(result["publication_authorized"])
        self.assertNotIn("media_publish",db.calls[0][0])
        self.assertNotIn("publication_reservations",db.calls[0][0])

    def test_past_date_fails_before_db(self):
        db = DB()
        with self.assertRaises(ValueError):
            transition_editorial(db,post_key=POST["post_key"],from_state="approved",
                to_state="planned",planned_at=NOW-timedelta(minutes=1),now=NOW)
        self.assertFalse(db.calls)

    def test_due_report_read_only(self):
        db=DB(next_rows=[("test-post","f"*64,NOW-timedelta(minutes=5))])
        due=inspect_due_plans(db,now=NOW)
        self.assertEqual(len(due),1)
        self.assertEqual(due[0]["action"],"requires_separate_explicit_approval")
        self.assertFalse(due[0]["publication_authorized"])
        self.assertTrue(db.calls[0][0].strip().startswith("SELECT"))

    def test_schema_private_no_publish_operation(self):
        schema=Path("supabase/migrations/20261030_presssport_editorial_queue.sql").read_text()
        self.assertIn("ENABLE ROW LEVEL SECURITY",schema)
        self.assertIn("REVOKE ALL",schema)
        self.assertIn("guard_editorial_queue",schema)
        self.assertIn("SECURITY INVOKER",schema)
        self.assertNotIn("media_publish",schema)
        self.assertNotIn("publication_reservations\nSET",schema)

if __name__ == "__main__":
    unittest.main()
