import hashlib
import unittest
from pathlib import Path
from scripts.presssport_verification_packet import build_packet

class VerificationPacketTests(unittest.TestCase):
    def test_packet_matches_manifest_and_cannot_publish(self):
        packet=build_packet()
        raw=Path("publishing/presssport-2026-10-28.json").read_bytes()
        self.assertEqual(packet["manifest_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(packet["image_count"],7)
        self.assertEqual(len(packet["image_urls"]),7)
        self.assertFalse(packet["publication_authorized"])
        self.assertFalse(packet["live_release_certified"])
        self.assertFalse(packet["live_publication_performed"])
        self.assertEqual(packet["executor_boundary"]["external_calls"],0)
        self.assertTrue(all(packet["offline_security_checks"].values()))

if __name__=="__main__":unittest.main()
