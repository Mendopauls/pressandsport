"""Static regression checks for the non-deployed reservation schema."""
import unittest
from pathlib import Path

SQL = (Path(__file__).resolve().parents[1] / "sql/presssport_publication_reservations.sql").read_text(encoding="utf-8").lower()

class ReservationSchemaTests(unittest.TestCase):
    def test_unique_publication_key(self):
        self.assertIn("publication_key text primary key", SQL)
    def test_attempt_identifier_unique(self):
        self.assertIn("attempt_id uuid not null unique", SQL)
    def test_row_level_security(self):
        self.assertIn("enable row level security", SQL)
    def test_public_roles_revoked(self):
        self.assertIn("revoke all on schema presssport_internal from public, anon, authenticated", SQL)
        self.assertIn("revoke all on all tables in schema presssport_internal from public, anon, authenticated", SQL)
    def test_uncertain_requires_reconciliation(self):
        self.assertIn("state <> 'uncertain' or reconciliation_required = true", SQL)
    def test_published_requires_media_id(self):
        self.assertIn("state <> 'published' or meta_media_id is not null", SQL)

if __name__ == "__main__":
    unittest.main()
