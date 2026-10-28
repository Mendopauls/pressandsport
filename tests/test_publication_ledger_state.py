"""Offline state machine regression tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publication_ledger_state import publication_key, validate_ledger, duplicate_blockers

ACCOUNT = "17841425937268080"
URLS = ["https://example.org/one.jpg"]
KEY = publication_key(ACCOUNT, URLS)
def entry(status, **extra):
    return {"instagram_account_id": ACCOUNT, "image_urls": URLS, "publication_key": KEY, "status": status, **extra}

class LedgerStateTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(validate_ledger([]), [])
    def test_reserved_blocks(self):
        self.assertTrue(duplicate_blockers({"instagram_account_id": ACCOUNT, "image_urls": URLS}, [entry("reserved")]))
    def test_uncertain_blocks(self):
        self.assertTrue(duplicate_blockers({"instagram_account_id": ACCOUNT, "image_urls": URLS}, [entry("uncertain", attempt_id="a", reconciliation_required=True)]))
    def test_published_blocks(self):
        self.assertTrue(duplicate_blockers({"instagram_account_id": ACCOUNT, "image_urls": URLS}, [entry("published", attempt_id="a", meta_media_id="123")]))
    def test_duplicate_active_blocks(self):
        self.assertTrue(validate_ledger([entry("reserved"), entry("reserved")]))
    def test_missing_meta_id_blocks(self):
        self.assertTrue(validate_ledger([entry("published", attempt_id="a")]))
    def test_unknown_state_blocks(self):
        self.assertTrue(validate_ledger([entry("retrying")]))
    def test_different_media_allowed(self):
        self.assertEqual(duplicate_blockers({"instagram_account_id": ACCOUNT, "image_urls": ["https://example.org/two.jpg"]}, [entry("reserved")]), [])
    def test_cancelled_releases(self):
        self.assertEqual(duplicate_blockers({"instagram_account_id": ACCOUNT, "image_urls": URLS}, [entry("cancelled")]), [])

if __name__ == "__main__":
    unittest.main()
