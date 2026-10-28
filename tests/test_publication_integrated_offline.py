"""End-to-end offline simulation: real builders and status validators, fake Meta transport.

No network, no secrets, no database writes and no publishing.
"""
import json
import unittest
from pathlib import Path
from scripts.meta_carousel_requests import child_requests, parent_request, publish_request
from scripts.meta_container_status import classify_container_status, require_all_ready
from scripts.meta_publisher_execution_plan import build_execution_plan
from scripts.check_publication_authorization import validate

MANIFEST = Path("publishing/presssport-2026-10-28.json").read_bytes()
AUTH = json.loads(Path("publishing/presssport-2026-10-28-authorization.json").read_text())

class SimulatedMeta:
    def __init__(self, child_status="FINISHED", parent_status="FINISHED"):
        self.requests = []
        self.child_status = child_status
        self.parent_status = parent_status
    def post(self, descriptor):
        self.requests.append(descriptor)
        return str(100000 + len(self.requests))
    def status(self, container_id, parent=False):
        return {"id": container_id,
                "status_code": self.parent_status if parent else self.child_status}

def simulate(manifest, meta):
    child_ids = [meta.post(request) for request in child_requests(manifest)]
    require_all_ready(child_ids, [meta.status(cid) for cid in child_ids])
    parent_id = meta.post(parent_request(manifest, child_ids))
    if classify_container_status(parent_id, meta.status(parent_id, parent=True)) != "ready":
        raise ValueError("parent container not ready")
    # Build the final request, but NEVER send it.
    final = publish_request(manifest, parent_id)
    return {"child_count": len(child_ids), "requests_sent_to_fake": len(meta.requests),
            "final_request_built": final["path"].endswith("/media_publish"),
            "publish_request_sent": False}

class IntegratedOfflineTests(unittest.TestCase):
    def test_happy_path_does_not_publish(self):
        fake = SimulatedMeta()
        result = simulate(MANIFEST, fake)
        self.assertEqual(result["child_count"], 7)
        self.assertEqual(result["requests_sent_to_fake"], 8)
        self.assertTrue(result["final_request_built"])
        self.assertFalse(result["publish_request_sent"])
        self.assertTrue(all(r["path"].endswith("/media") for r in fake.requests))
    def test_pending_children_block_parent(self):
        fake = SimulatedMeta(child_status="IN_PROGRESS")
        with self.assertRaises(ValueError):
            simulate(MANIFEST, fake)
        self.assertEqual(len(fake.requests), 7)
    def test_failed_children_block_parent(self):
        fake = SimulatedMeta(child_status="ERROR")
        with self.assertRaises(ValueError):
            simulate(MANIFEST, fake)
        self.assertEqual(len(fake.requests), 7)
    def test_pending_parent_blocks_publish(self):
        fake = SimulatedMeta(parent_status="IN_PROGRESS")
        with self.assertRaises(ValueError):
            simulate(MANIFEST, fake)
        self.assertEqual(len(fake.requests), 8)
    def test_expired_parent_blocks_publish(self):
        fake = SimulatedMeta(parent_status="EXPIRED")
        with self.assertRaises(ValueError):
            simulate(MANIFEST, fake)
        self.assertEqual(len(fake.requests), 8)
    def test_invalid_authorization_blocks_execution_plan(self):
        self.assertTrue(validate(MANIFEST, AUTH))
        with self.assertRaises(PermissionError):
            build_execution_plan(MANIFEST, AUTH, identity_verified=True)
    def test_identity_unverified_blocks_execution_plan(self):
        with self.assertRaises(PermissionError):
            build_execution_plan(MANIFEST, AUTH, identity_verified=False)

if __name__ == "__main__":
    unittest.main()
