import unittest
from scripts.presssport_release_audit import audit

class ReleaseAuditTests(unittest.TestCase):
    def test_component_inventory(self):
        result = audit()
        self.assertEqual(result["components_present"], result["components_required"])
        self.assertEqual(result["missing_components"], [])
    def test_publication_remains_disabled(self):
        self.assertFalse(audit()["publication_authorized"])
    def test_release_ready_requires_runner(self):
        result = audit()
        self.assertTrue(result["production_runner_present"])
        self.assertEqual(result["runner_mode"], "dry_run_only")
        self.assertFalse(result["release_ready"])

if __name__ == "__main__":
    unittest.main()
