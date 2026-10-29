import unittest
from scripts.presssport_recovery_triage import recovery_decision, recovery_report

class RecoveryTriageTests(unittest.TestCase):
    def test_no_state_allows_automatic_retry(self):
        for state in ("reserved","publishing","uncertain","published","failed","cancelled","other"):
            for stale in (False, True):
                for reconcile in (False, True):
                    with self.subTest(state=state,stale=stale,reconcile=reconcile):
                        result=recovery_decision(state,stale=stale,
                                                 reconciliation_required=reconcile)
                        self.assertIn(result["action"],{"wait","manual_review","no_retry","block"})
    def test_stalled_publishing_requires_manual_review(self):
        self.assertEqual(recovery_decision("publishing",stale=True)["action"],"manual_review")
    def test_uncertain_requires_manual_review_even_without_media_id(self):
        self.assertEqual(recovery_decision("uncertain")["action"],"manual_review")
    def test_published_requires_valid_media_id(self):
        self.assertEqual(recovery_decision("published",media_id="12345")["action"],"no_retry")
        self.assertEqual(recovery_decision("published")["action"],"manual_review")
    def test_reserved_does_not_start_new_attempt(self):
        self.assertEqual(recovery_decision("reserved")["action"],"wait")
    def test_report_keeps_key_and_never_suggests_retry(self):
        result=recovery_report([{"publication_key":"abc","state":"uncertain"}])
        self.assertEqual(result[0]["publication_key"],"abc")
        self.assertEqual(result[0]["action"],"manual_review")

if __name__=="__main__": unittest.main()
