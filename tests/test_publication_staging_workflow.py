import unittest
from pathlib import Path

class StagingWorkflowTests(unittest.TestCase):
    def test_staging_runs_on_main_and_manually(self):
        text=Path(".github/workflows/presssport-cloud-executor-staging.yml").read_text()
        self.assertIn("workflow_dispatch:",text)
        self.assertIn("push:",text)
        self.assertIn("branches: [main]",text)
        self.assertIn("python -m scripts.presssport_cloud_executor_staging",text)
        self.assertNotIn("secrets.",text)
if __name__=="__main__":unittest.main()
