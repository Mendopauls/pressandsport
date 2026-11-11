"""Offline regression tests for staged import and caption validation."""
import unittest
from pathlib import Path
from scripts.presssport_caption_quality import validate_draft, repair_prompt, validate_then_repair

ROOT = Path(__file__).resolve().parents[1]
def good():
    return {"instagram_caption": "I" * 500, "linkedin_caption": "L" * 750,
            "visual_brief": "grafica neutra", "fact_checks": "da verificare",
            "suggested_alt_text": "testo alternativo"}

class StagedTests(unittest.TestCase):
    def test_import_checks_marker_and_duplicate(self):
        app = (ROOT / "integrations/google-drive/presssport_drive_queue.gs").read_text()
        self.assertIn("PS_OLLAMA_READY__", app)
        self.assertIn("PS_OLLAMA_READY=YES", app)
        self.assertIn("NON PUBBLICARE", app)
        self.assertIn("status === 201 || status === 409", app)
        self.assertIn("everyMinutes(15)", app)
        self.assertIn("X-Drive-Ingest-Secret", app)

    def test_server_only_enqueues_presssport(self):
        edge = (ROOT / "supabase/functions/presssport-drive-ingest/index.ts").read_text()
        self.assertIn("PRESSSPORT_DRIVE_INGEST_SECRET", edge)
        self.assertIn('body.project_slug!=="press-sport"', edge)
        self.assertIn('jobKey!=="ps-drive-"+fileId', edge)
        self.assertIn('admin.rpc("presssport_worker_enqueue"', edge)
        self.assertIn('publication:false', edge)
        for token in ("graph.facebook.com", "api.linkedin.com", "META_INSTAGRAM_ACCESS_TOKEN"):
            self.assertNotIn(token, edge)

    def test_invalid_and_short(self):
        self.assertIn("invalid_json", validate_draft("not json"))
        row = good()
        row["instagram_caption"] = "short"
        self.assertTrue(validate_draft(row))
        self.assertIn("NON PUBBLICARE", repair_prompt("brief", row))

    def test_valid_never_auto_approves(self):
        result = validate_then_repair("brief", good(), lambda _: self.fail("unexpected retry"))
        self.assertEqual(result["retries"], 0)
        self.assertTrue(result["needs_human_review"])

    def test_one_retry(self):
        row = good()
        row["linkedin_caption"] = "short"
        calls = []
        def generate(prompt):
            calls.append(prompt)
            return good()
        result = validate_then_repair("brief", row, generate)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["retries"], 1)
        self.assertTrue(result["needs_human_review"])

    def test_unfixed_remains_blocked(self):
        row = good()
        row["linkedin_caption"] = "short"
        result = validate_then_repair("brief", row, lambda _: row)
        self.assertTrue(result["issues"])
        self.assertTrue(result["needs_human_review"])

if __name__ == "__main__":
    unittest.main()
