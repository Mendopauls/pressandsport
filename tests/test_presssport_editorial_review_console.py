"""Offline smoke tests for the production editorial console, no credentials or live publication."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class EditorialConsoleTests(unittest.TestCase):
    def test_review_page_has_authentication(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn("signInWithPassword",html)
        self.assertIn("presssport-v2-web-session",html)
        self.assertIn("callJobs(\"list\")",html)

    def test_revision_history_is_separate_from_original(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn('callJobs("revision"',html)
        self.assertIn("latest_editorial_content",html)
        self.assertIn("Revisioni conservate",html)

    def test_no_publication_actions_in_review_console(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertNotIn('callJobs("publish"',html)
        self.assertNotIn('callJobs("approve"',html)
        self.assertIn("Checklist pre-pubblicazione",html)

    def test_asset_verification_is_explicit(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn('item.asset_state==="verified"',html)
        self.assertIn('callJobs("asset"',html)
        self.assertIn("Approvazione umana",html)

if __name__=="__main__":unittest.main()
