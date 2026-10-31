import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.presssport_ollama_worker import connect,discover,process_one

class WorkerTests(unittest.TestCase):
    def test_resume_running_state(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);db=connect(root)
            db.execute("INSERT INTO jobs(job_key,source_file,state,updated) VALUES('abc','/tmp/a','running','x')")
            db.commit();db.close()
            db=connect(root)
            self.assertEqual(db.execute("SELECT state FROM jobs WHERE job_key='abc'").fetchone()[0],"pending")
    def test_dedup_same_key_and_draft(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);db=connect(root)
            inbox=root/"inbox";inbox.mkdir()
            (inbox/"first.json").write_text('{"job_key":"post-01","brief":"Sport e comunicazione"}',encoding="utf-8")
            discover(db,root);discover(db,root)
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0],1)
            with patch("scripts.presssport_ollama_worker.generate",return_value="Testo da revisionare"):
                self.assertTrue(process_one(db,root,"http://127.0.0.1:11434","model"))
            self.assertIn("draft_for_review",(root/"drafts"/"post-01.json").read_text(encoding="utf-8"))
            discover(db,root)
            self.assertEqual(db.execute("SELECT state FROM jobs").fetchone()[0],"complete")
    def test_failed_work_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);db=connect(root);(root/"inbox").mkdir()
            (root/"inbox"/"x.json").write_text('{"job_key":"x","brief":"Test"}')
            discover(db,root)
            with patch("scripts.presssport_ollama_worker.generate",side_effect=ConnectionError):
                self.assertFalse(process_one(db,root,"http://127.0.0.1:11434","model"))
            self.assertTrue((root/"inbox"/"x.json").exists())
if __name__=="__main__":unittest.main()
