import unittest
from pathlib import Path

class EvidenceWorkflowTests(unittest.TestCase):
    def test_cloud_evidence_only_on_success(self):
        source=Path(".github/workflows/presssport-cloud-publisher-dryrun.yml").read_text()
        self.assertIn("python -m scripts.presssport_cloud_publisher",source)
        self.assertIn("if: success()",source)
        self.assertIn("actions/upload-artifact@v4",source)
        self.assertIn("presssport-cloud-readonly-verification",source)
        self.assertIn("No publication performed",source)
        self.assertNotIn("execute_once",source)
        self.assertNotIn("presssport_publication_orchestrator",source)
if __name__=="__main__":unittest.main()
