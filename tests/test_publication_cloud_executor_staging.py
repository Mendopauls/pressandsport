import unittest
from scripts.presssport_cloud_executor_staging import run

class CloudExecutorStagingTests(unittest.TestCase):
    def test_staging_does_not_publish(self):
        result=run()
        self.assertEqual(result["mode"],"staging_only")
        self.assertTrue(result["security_audit_passed"])
        self.assertFalse(result["live_execution_enabled"])
        self.assertFalse(result["published"])
        self.assertEqual(result["image_count"],7)

if __name__=="__main__":unittest.main()
