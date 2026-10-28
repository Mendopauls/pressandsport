import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from scripts.meta_publisher_execution_plan import build_execution_plan

MANIFEST = Path("publishing/presssport-2026-10-28.json")

class PublisherExecutionPlanTests(unittest.TestCase):
    def test_current_authorization_denied(self):
        auth = json.loads(Path("publishing/presssport-2026-10-28-authorization.json").read_text())
        with self.assertRaises(PermissionError):
            build_execution_plan(MANIFEST.read_bytes(), auth, identity_verified=True)
    def test_identity_not_verified_denied(self):
        with patch("scripts.meta_publisher_execution_plan.validate", return_value=[]):
            with self.assertRaises(PermissionError):
                build_execution_plan(MANIFEST.read_bytes(), {}, identity_verified=False)
    def test_steps_order_and_single_publish(self):
        with patch("scripts.meta_publisher_execution_plan.validate", return_value=[]):
            plan = build_execution_plan(MANIFEST.read_bytes(), {}, identity_verified=True)
        self.assertEqual(plan["image_count"], 7)
        self.assertEqual(plan["steps"].count("publish_parent_once"), 1)
        self.assertLess(plan["steps"].index("commit_reservation"), plan["steps"].index("publish_parent_once"))
        self.assertLess(plan["steps"].index("commit_publishing_state"), plan["steps"].index("publish_parent_once"))
        self.assertEqual(plan["steps"][-1], "record_published_or_uncertain")
        self.assertEqual(plan["mode"], "PLAN_ONLY_NO_SIDE_EFFECTS")

if __name__ == "__main__":
    unittest.main()
