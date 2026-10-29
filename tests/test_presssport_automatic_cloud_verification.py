import unittest
from pathlib import Path
class CloudVerificationWorkflowTests(unittest.TestCase):
    def test_readonly_cloud_check_is_automated(self):
        content=Path(".github/workflows/presssport-cloud-publisher-dryrun.yml").read_text()
        self.assertIn("workflow_dispatch:",content)
        self.assertIn("push:",content)
        self.assertIn("branches: [main]",content)
        self.assertIn("python -m scripts.presssport_cloud_publisher",content)
        self.assertNotIn("presssport_publication_orchestrator",content)
        self.assertNotIn("execute_once",content)
        self.assertNotIn("publish_now",content)
if __name__=="__main__":unittest.main()
