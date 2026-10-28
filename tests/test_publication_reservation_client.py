import json
import unittest
from unittest.mock import MagicMock
from scripts.publication_reservation import reserve_publication
from scripts.publication_ledger_state import publication_key

class ReservationClientTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"status":"approved","instagram_account_id":"123","image_urls":["https://example.com/a.jpg"]}
        self.db = MagicMock()
        self.cursor = self.db.cursor.return_value.__enter__.return_value
        self.cursor.fetchone.return_value = (publication_key("123",self.manifest["image_urls"]),)
    def run_reservation(self, manifest=None):
        return reserve_publication(self.db, json.dumps(manifest or self.manifest).encode(), "00000000-0000-0000-0000-000000000001")
    def test_insert_contains_unique_key_and_digest(self):
        result = self.run_reservation()
        self.assertEqual(result["publication_key"], publication_key("123",self.manifest["image_urls"]))
        sql, params = self.cursor.execute.call_args.args
        self.assertIn("INSERT INTO presssport_internal.publication_reservations",sql)
        self.assertEqual(params[0],result["publication_key"])
        self.assertEqual(params[3],"00000000-0000-0000-0000-000000000001")
    def test_reject_unapproved(self):
        with self.assertRaises(ValueError):
            self.run_reservation({**self.manifest,"status":"draft"})
        self.cursor.execute.assert_not_called()
    def test_reject_insecure_media(self):
        with self.assertRaises(ValueError):
            self.run_reservation({**self.manifest,"image_urls":["http://example.com/a.jpg"]})
        self.cursor.execute.assert_not_called()
    def test_duplicate_database_error_propagates(self):
        self.cursor.execute.side_effect = RuntimeError("unique violation")
        with self.assertRaisesRegex(RuntimeError,"unique violation"):
            self.run_reservation()
    def test_unconfirmed_reservation_fails_closed(self):
        self.cursor.fetchone.return_value = None
        with self.assertRaisesRegex(RuntimeError,"not confirmed"):
            self.run_reservation()
    def test_no_commit_inside_primitive(self):
        self.run_reservation()
        self.db.commit.assert_not_called()

if __name__ == "__main__":
    unittest.main()
