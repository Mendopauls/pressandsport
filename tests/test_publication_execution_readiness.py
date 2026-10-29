import json
import unittest
from pathlib import Path
from scripts.presssport_execution_readiness import assess

class ReadinessTests(unittest.TestCase):
    def test_authorization_disabled(self):
        manifest=Path("publishing/presssport-2026-10-28.json").read_bytes()
        auth=json.loads(Path("publishing/presssport-2026-10-28-authorization.json").read_text())
        result=assess(manifest,auth)
        self.assertFalse(result["live_execution_enabled"])
        self.assertGreater(len(result["authorization_blockers"]),0)
        self.assertEqual(result["image_count"],7)
if __name__=="__main__":unittest.main()
