import unittest
from unittest.mock import patch
from scripts.presssport_preproduction_audit import inspect_preproduction

class PreproductionAuditTests(unittest.TestCase):
    def test_safe_repository_is_not_release_ready(self):
        result=inspect_preproduction()
        self.assertTrue(result["passed"])
        self.assertFalse(result["release_ready"])
        self.assertFalse(result["publication_performed"])
    def test_missing_component_blocks(self):
        with patch("scripts.presssport_preproduction_audit.audit",
                   return_value={"release_ready":False,"runner_mode":"dry_run_only",
                                 "missing_components":["missing"]}):
            result=inspect_preproduction()
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["all_components_present"])

if __name__=="__main__": unittest.main()
