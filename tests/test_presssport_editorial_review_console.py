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

    def test_revision_editor_enforces_caption_lengths(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn("Lunghezza caption fuori dai limiti editoriali",html)
        self.assertIn("content.instagram_caption.length<450",html)
        self.assertIn("content.linkedin_caption.length<650",html)

    def test_revision_api_and_migration_enforce_limits(self):
        migration_path=ROOT/"supabase"/"migrations"/"20261101_editorial_revision_caption_validation.sql"
        self.assertTrue(migration_path.exists(), "Migration missing from checked-out branch")
        migration=migration_path.read_text(encoding="utf-8")
        self.assertIn("char_length(ig) not between 450 and 750",migration)
        self.assertIn("char_length(li) not between 650 and 1000",migration)
        self.assertIn("grant execute",migration)
        for name in ("visual_brief","fact_checks","suggested_alt_text"):
            self.assertIn(name,migration)

    def test_asset_verification_is_explicit(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn('item.asset_state==="verified"',html)
        self.assertIn('callJobs("asset"',html)
        self.assertIn("Approvazione umana",html)

if __name__=="__main__":unittest.main()
